import ast
from datetime import timedelta
from pathlib import Path
import numpy as np
from sqlalchemy import select
from app.ai import matcher, reranking
from app.config import settings
from app.core.clock import now
from app.core.database import SessionLocal
from app.models import CV, Job, Order, Subscription
from app.services.common import embed_cv
from app.services import applications as application_service
from app.tasks.embedding_tasks import build_embedding
from tests.conftest import CV_TEXT
from tests.test_flows import _order, _webhook, apply

APP_DIR = Path(__file__).resolve().parents[1] / "app"


def test_dependency_boundaries():
    for file in (APP_DIR / "api/v1").glob("*.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert not (isinstance(node.func.value, ast.Name) and node.func.value.id == "db"), file
            if isinstance(node, ast.ImportFrom) and node.level:
                assert not (node.module or "").startswith(("repositories", "ai")), file
    for file in (APP_DIR / "repositories").glob("*.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("services", "api")), file


def test_worker_uses_committed_revision_and_ignores_stale_work(world, monkeypatch):
    dispatched = []
    monkeypatch.setattr(settings, "task_always_eager", False)
    monkeypatch.setattr(build_embedding, "delay", lambda *args: dispatched.append(args))
    client, headers = (world["c"], world["cands"][0])
    response = client.post("/api/v1/cvs", data={"text": CV_TEXT}, headers=headers)
    assert response.status_code == 200
    cv_id = response.json()["id"]
    assert response.json()["processing_status"] == "PENDING"
    first = dispatched[-1]
    response = client.put(f"/api/v1/cvs/{cv_id}", json={"skills": ["Python", "Docker"]}, headers=headers)
    assert response.status_code == 200
    current = dispatched[-1]
    assert current[2] > first[2]
    assert build_embedding.run(*first) == "obsolete"
    assert build_embedding.run(*current) == "ready"
    with SessionLocal() as db:
        cv = db.get(CV, cv_id)
        assert cv.embedding is not None and cv.processing_status == "READY"
        assert cv.embedding_model == "hashing"


def test_rolled_back_embedding_is_not_dispatched(world, monkeypatch):
    dispatched = []
    monkeypatch.setattr(settings, "task_always_eager", False)
    monkeypatch.setattr(build_embedding, "delay", lambda *args: dispatched.append(args))
    with SessionLocal() as db:
        cv = db.scalar(select(CV).limit(1))
        embed_cv(cv)
        db.rollback()
    assert dispatched == []


def test_cross_encoder_changes_retrieval_order(world, monkeypatch):
    with SessionLocal() as db:
        job = db.get(Job, world["job"]["id"])
        cvs = db.scalars(select(CV).order_by(CV.id)).all()
        monkeypatch.setattr(matcher, "retrieve", lambda *args: [(cvs[0], 0.95), (cvs[1], 0.8)])
        monkeypatch.setattr(matcher, "score_pairs", lambda pairs: [0.1, 0.9])
        ranked = matcher.rank_cvs_for_job(db, job, k=2)
        assert ranked[0][0].id == cvs[1].id
        assert ranked[0][1]["reranking"] == "cross-encoder"


def test_cross_encoder_normalizes_logits(monkeypatch):

    class Predictor:
        def predict(self, pairs, **kwargs):
            return np.array([-2.0, 2.0])

    monkeypatch.setattr(reranking, "get_cross_encoder", lambda: Predictor())
    scores = reranking.score_pairs([("cv", "jd"), ("cv2", "jd2")])
    assert 0 < scores[0] < 0.5 < scores[1] < 1


def test_cv_evaluation_requires_premium_and_separates_scores(world):
    client, headers = (world["c"], world["cands"][0])
    cv_id = client.get("/api/v1/cvs", headers=headers).json()[0]["id"]
    query = {"cv_id": cv_id, "job_id": world["job"]["id"]}
    assert client.get("/api/v1/matching/cv-evaluation", params=query, headers=headers).status_code == 403
    order = _order(client, headers, "CAND")
    _webhook(client, "EVALUATION-TX", order["order_code"], order["amount"])
    response = client.get("/api/v1/matching/cv-evaluation", params=query, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert 0 <= result["cv_score"] <= 100 and 0 <= result["match_score"] <= 1
    assert "Kafka" in result["missing_skills"] and result["can_apply"] is True
    assert all(("Nếu" in item["suggestion"] or "chỉ bổ sung" in item["suggestion"] for item in result["suggestions"]))
    assert (
        client.get("/api/v1/matching/cv-evaluation", params={"cv_id": cv_id}, headers=headers).json()["match_score"]
        is None
    )
    other_cv = client.get("/api/v1/cvs", headers=world["cands"][1]).json()[0]["id"]
    assert client.get("/api/v1/matching/cv-evaluation", params={"cv_id": other_cv}, headers=headers).status_code == 404


def test_hr_recommendations_hide_identity_until_application(world):
    client, hr = (world["c"], world["hr"])
    route = f"/api/v1/jobs/{world['job']['id']}/candidates"
    before = client.get(route, headers=hr).json()
    assert all((item["candidate"]["full_name"].startswith("Ứng viên #") for item in before))
    assert all((item["cv"]["title"].startswith("Hồ sơ #") for item in before))
    application = apply(world)
    assert client.get(f"/api/v1/cvs/{application['cv']['id']}", headers=hr).status_code == 403
    after = client.get(route, headers=hr).json()
    assert (
        next((item for item in after if item["candidate"]["id"] == application["candidate"]["id"]))["candidate"][
            "full_name"
        ]
        == application["candidate"]["full_name"]
    )


def test_premium_requires_active_subscription(world):
    client, headers = world["c"], world["cands"][0]
    cv_id = client.get("/api/v1/cvs", headers=headers).json()[0]["id"]
    order = _order(client, headers, "CAND")
    _webhook(client, "REVOKED-PREMIUM", order["order_code"], order["amount"])
    with SessionLocal() as db:
        subscription = db.scalar(select(Subscription).where(Subscription.order_id == order["id"]))
        subscription.active = False
        db.commit()
    assert client.get("/api/v1/users/me", headers=headers).json()["user"]["is_premium"] is False
    assert client.get("/api/v1/matching/cv-evaluation", params={"cv_id": cv_id}, headers=headers).status_code == 403
    assert client.get("/api/v1/matching/jobs", headers=headers).status_code == 200


def test_hr_can_close_only_owned_job_and_cannot_publish(world):
    client, hr, candidate = world["c"], world["hr"], world["cands"][0]
    path = f"/api/v1/jobs/{world['job']['id']}/status"
    assert client.patch(path, json={"status": "CLOSED"}, headers=candidate).status_code == 403
    assert client.patch(path, json={"status": "PUBLISHED"}, headers=hr).status_code == 422
    assert client.patch(path, json={"status": "CLOSED"}, headers=hr).status_code == 200
    assert client.get("/api/v1/jobs").json()["total"] == 0


def test_model_failure_does_not_block_application_or_hr_review(world, monkeypatch):
    def unavailable(*args):
        raise RuntimeError("Cross-Encoder unavailable")

    monkeypatch.setattr(application_service, "match_pair", unavailable)
    application = apply(world)
    assert application["status"] == "NEW" and application["match_score"] is None
    response = world["c"].get(f"/api/v1/applications/{application['id']}/manage", headers=world["hr"])
    assert response.status_code == 200 and response.json()["cv"]["raw_text"] == CV_TEXT


def test_explicit_fallback_uses_actual_embedding_model(world, monkeypatch):
    # The active embedder is hashing, as it would be after an explicitly permitted fallback.
    monkeypatch.setattr(settings, "embed_model", "unavailable-pretrained-model")
    monkeypatch.setattr(settings, "allow_hashing_fallback", True)
    response = world["c"].get("/api/v1/matching/jobs", headers=world["cands"][0])
    assert response.status_code == 200 and response.json()["items"]
    response = world["c"].get(f"/api/v1/jobs/{world['job']['id']}/candidates", headers=world["hr"])
    assert response.status_code == 200 and len(response.json()) == 2


def test_reapplication_after_withdrawal_preserves_history(world):
    first = apply(world)
    client, headers = (world["c"], world["cands"][0])
    assert client.post(f"/api/v1/applications/{first['id']}/withdraw", headers=headers).status_code == 200
    second = apply(world)
    assert first["id"] != second["id"]
    history = client.get("/api/v1/applications", headers=headers).json()
    assert len(history) == 2 and {item["status"] for item in history} == {"NEW", "WITHDRAWN"}


def test_late_payment_does_not_activate_pending_order(world):
    client, headers = (world["c"], world["cands"][0])
    order = _order(client, headers, "CAND")
    with SessionLocal() as db:
        db.get(Order, order["id"]).expires_at = now() - timedelta(seconds=10)
        db.commit()
    assert _webhook(client, "LATE-TX", order["order_code"], order["amount"]).json()["status"] == "LATE"
    assert client.get("/api/v1/users/me", headers=headers).json()["user"]["is_premium"] is False


def test_matching_excludes_vectors_from_another_model(world):
    with SessionLocal() as db:
        db.get(Job, world["job"]["id"]).embedding_model = "another-model"
        db.commit()
    response = world["c"].get("/api/v1/matching/jobs", headers=world["cands"][0])
    assert response.status_code == 200 and response.json()["items"] == []
    assert apply(world)["match_score"] is None

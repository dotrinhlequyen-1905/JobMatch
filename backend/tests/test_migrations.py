import json
import os
from pathlib import Path
import sqlite3
import struct
import subprocess
import sys
import pytest


def migrate(db, revision):
    backend = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db.as_posix()}"}
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(backend / "alembic.ini"), "upgrade", revision],
        cwd=backend,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_migration_preserves_legacy_cv_vectors_and_relations(tmp_path):
    db = tmp_path / "legacy.db"
    migrate(db, "0001")
    vector = struct.pack("<3f", 0.1, 0.2, 0.3)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO users (id,email,password_hash,full_name,role,status,created_at) VALUES (1,'migration@example.vn','hash','Candidate','CANDIDATE','ACTIVE','2026-01-01')"
        )
        connection.execute(
            "INSERT INTO cvs (id,candidate_id,title,raw_text,parsed,skills,years,seniority,role,is_default,embedding,created_at) VALUES (1,1,'Legacy CV','Legacy text','{}','[]',1,'junior','software_engineer',1,?,'2026-01-01')",
            (vector,),
        )
    migrate(db, "head")
    with sqlite3.connect(db) as connection:
        cv = connection.execute("SELECT embedding,embedding_model,processing_status,candidate_id FROM cvs").fetchone()
        assert json.loads(cv[0]) == pytest.approx([0.1, 0.2, 0.3])
        assert cv[1:] == ("legacy", "READY", 1)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(applications)")}
        assert "uq_application_active" in indexes


def test_spec_completion_migration_backfills_skills_and_verifies_existing_users(tmp_path):
    db = tmp_path / "skills.db"
    migrate(db, "0002")
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO users (id,email,password_hash,full_name,role,status,created_at) VALUES (1,'old@example.vn','hash','Old','CANDIDATE','ACTIVE','2026-01-01')"
        )
        connection.execute(
            "INSERT INTO cvs (id,candidate_id,title,raw_text,parsed,skills,years,seniority,role,is_default,created_at) VALUES (1,1,'CV','text','{}','[\"Python\",\"Docker\",\"Python\"]',1,'junior','software_engineer',1,'2026-01-01')"
        )
    migrate(db, "head")
    with sqlite3.connect(db) as connection:
        names = {r[0] for r in connection.execute("SELECT s.name FROM cv_skills c JOIN skills s ON s.id = c.skill_id WHERE c.cv_id = 1")}
        assert names == {"Python", "Docker"}
        assert connection.execute("SELECT email_verified_at FROM users WHERE id = 1").fetchone()[0] is not None
        assert connection.execute("SELECT view_count FROM jobs").fetchall() == []
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

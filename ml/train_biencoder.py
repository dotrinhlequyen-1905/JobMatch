"""Fine-tune bi-encoder so khớp CV–JD (vừa GPU 6GB: fp16 + CachedMNRL).

  python ml/train_biencoder.py                                  # e5-base, text profile, 3 epoch
  python ml/train_biencoder.py --model bkai --text profile
  python ml/train_biencoder.py --max-steps 20                   # chạy thử nhanh

Dữ liệu: data/final/train_triplets_{text}.jsonl (anchor=JD, positive=CV phù hợp, negative=CV không/ít phù hợp)
Đánh giá trong lúc train: NDCG@10 trên val (InformationRetrievalEvaluator).
Kết quả: models/cvjd-<model>-<text>/  -> đặt EMBED_MODEL=models/... trong backend/.env để web dùng.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {"e5-base": "intfloat/multilingual-e5-base", "e5-small": "intfloat/multilingual-e5-small",
           "bkai": "bkai-foundation-models/vietnamese-bi-encoder",
           "mpnet": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="e5-base")
    ap.add_argument("--text", default="profile", choices=["profile", "full"])
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--batch", type=int, default=64, help="batch hiệu dụng (số JD mỗi bước)")
    ap.add_argument("--mini-batch", type=int, default=16, help="giảm nếu hết VRAM (8, 4)")
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument("--data", default="orig", choices=["orig", "clean", "llm"],
                    help="orig: bộ ba gốc; clean: bỏ bộ ba LLM cho là nhãn sai; llm: clean + CV do LLM viết lại")
    a = ap.parse_args()

    from datasets import Dataset
    from sentence_transformers import (SentenceTransformer, SentenceTransformerTrainer,
                                       SentenceTransformerTrainingArguments, losses)
    from sentence_transformers.evaluation import InformationRetrievalEvaluator
    from sentence_transformers.training_args import BatchSamplers

    name = ALIASES.get(a.model, a.model)
    prefix = "query: " if "e5" in name.lower() else ""
    model = SentenceTransformer(name, device="cuda")
    model.max_seq_length = a.max_len

    suffix = "" if a.data == "orig" else f"_{a.data}"
    rows = [json.loads(l) for l in open(ROOT / f"data/final/train_triplets_{a.text}{suffix}.jsonl", encoding="utf-8")]
    print(f"Dữ liệu train: {len(rows)} bộ ba ({a.data}, {a.text})")
    train = Dataset.from_dict({k: [prefix + r[k] for r in rows] for k in ("anchor", "positive", "negative")})

    jobs = {j["job_id"]: j for j in map(json.loads, open(ROOT / "data/final/jobs.jsonl", encoding="utf-8"))}
    cvs = {c["cv_id"]: c for c in map(json.loads, open(ROOT / "data/final/cvs.jsonl", encoding="utf-8"))}
    val = json.load(open(ROOT / "data/final/val_ir.json", encoding="utf-8"))
    key = f"text_{a.text}"
    evaluator = InformationRetrievalEvaluator(
        queries={q: prefix + jobs[q][key] for q in val["queries"]},
        corpus={c: prefix + cvs[c][key] for c in val["corpus"]},
        relevant_docs={q: set(r) for q, r in val["qrels"].items() if r},
        name="val", ndcg_at_k=[10], mrr_at_k=[10], accuracy_at_k=[1, 10], precision_recall_at_k=[20],
        show_progress_bar=False, batch_size=32)

    out = ROOT / f"models/cvjd-{a.model.replace('/', '_')}-{a.text}{'' if a.data == 'orig' else '-' + a.data}"
    loss = losses.CachedMultipleNegativesRankingLoss(model, mini_batch_size=a.mini_batch)
    args = SentenceTransformerTrainingArguments(
        output_dir=str(out / "checkpoints"), num_train_epochs=a.epochs, max_steps=a.max_steps,
        per_device_train_batch_size=a.batch, learning_rate=a.lr, warmup_steps=0.1, fp16=True,
        batch_sampler=BatchSamplers.NO_DUPLICATES, eval_strategy="steps", eval_steps=25, save_strategy="steps",
        save_steps=25, save_total_limit=2, load_best_model_at_end=True, metric_for_best_model="val_cosine_ndcg@10",
        logging_steps=10, report_to="none", seed=42)
    print("Trước khi train:", {k: round(v, 4) for k, v in evaluator(model).items() if "ndcg" in k or "mrr" in k})
    trainer = SentenceTransformerTrainer(model=model, args=args, train_dataset=train, loss=loss, evaluator=evaluator)
    trainer.train()
    print("Sau khi train:", {k: round(v, 4) for k, v in evaluator(model).items() if "ndcg" in k or "mrr" in k})
    model.save(str(out))
    print(f"Đã lưu model: {out}\nDùng cho web: thêm dòng EMBED_MODEL=models/{out.name} vào backend/.env rồi chạy "
          f"'python backend/scripts/seed.py --reembed'")


if __name__ == "__main__":
    main()

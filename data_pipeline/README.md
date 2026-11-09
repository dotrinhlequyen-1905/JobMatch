# Pipeline tạo bộ dữ liệu so khớp CV–JD

```bash
.venv/Scripts/python.exe data_pipeline/run_all.py   # chạy lại toàn bộ (seed cố định -> kết quả giống nhau)
```

| Bước | Script | Đầu ra |
|---|---|---|
| 1. Làm sạch JD | `s01_clean_jobs.py` | `data/processed/jobs.jsonl`, `skills_vocab.json` |
| 2. Sinh CV bằng template | `s02_generate_cvs.py` | `data/processed/cvs.jsonl`, `pairs.jsonl` |
| 3. Chia train/val/test | `s03_split_export.py` | `data/final/*` |
| 4. Xuất CV ra PDF/DOCX | `s04_render_files.py` | `data/cv_files/*`, `ground_truth.jsonl` |
| 5. File gán nhãn tay | `s05_annotation_set.py` | `data/annotation/annotate_test.xlsx` |

Dùng chung: `vocab.py` (chuẩn hóa kỹ năng/vai trò/cấp bậc), `templates.py` (câu mẫu), `profile_text.py` (văn bản đưa vào mô hình).

## Nguồn dữ liệu
JD: [IT-Job-Posting](https://github.com/SonPhatTranDeveloper/IT-Job-Posting) — 3.101 tin IT từ LinkedIn, ITviec, TopCV (chỉ dùng cho mục đích học tập).
CV: sinh tổng hợp bằng template, không có dữ liệu cá nhân thật.

## Nhãn
| Loại CV | Cách sinh | Nhãn |
|---|---|---|
| `fit` | cùng vai trò, 80–100% kỹ năng JD, đủ số năm KN | 2 |
| `partial_skill` | cùng vai trò, 40–66% kỹ năng JD | 1 |
| `partial_senior` | đủ kỹ năng nhưng thiếu 2–3 năm KN | 1 |
| `hard_neg` | vai trò khác hẳn, chỉ trùng vài kỹ năng chung | 0 |

Val/test chấm lại **toàn bộ ma trận JD × CV** bằng `relevance()` trong `s03_split_export.py`
(khớp ~97–98% với nhãn gốc), tránh âm tính giả khi một CV hợp với nhiều JD.

## File trong `data/final/`
- `train_triplets_{full,profile}.jsonl`: `anchor` (JD), `positive`, `negative` → MultipleNegativesRankingLoss
- `train_pairs_{full,profile}.jsonl`: `jd`, `cv`, `score` ∈ {0, 0.5, 1} → CoSENT / cross-encoder
- `{val,test}_ir.json`: `queries` (job_id), `corpus` (cv_id), `qrels` {job_id: {cv_id: 1|2}} → InformationRetrievalEvaluator
- `jobs.jsonl`, `cvs.jsonl`: đầy đủ trường + `split`, `text_full`, `text_profile`

`full` = toàn văn (hợp multilingual-e5, 512 token); `profile` = bản rút gọn (hợp PhoBERT/bkai, 256 token).

## Hạn chế đã biết
- CV sinh bằng template nên câu văn còn lặp; đôi khi kỹ năng ghép vào câu chưa hợp ngữ cảnh.
- Nhãn val/test do luật chấm → cần tập gán nhãn tay (`annotate_test.xlsx`) để báo cáo kết quả đáng tin.
- Một số nhóm vai trò ít dữ liệu (data_analyst, blockchain, business_analyst).

## Tăng cường bằng LLM (bước 6)
- `llm/augment.py` (chạy nền, tự tiếp tục): Nemotron-3-Super viết lại CV cho tự nhiên (kiểm tra tự động: đủ kỹ năng,
  không bịa kỹ năng, đúng tên/ngôn ngữ); Nemotron-3-Ultra chấm lại nhãn (ưu tiên 500 cặp của file gán nhãn tay).
- `s06_merge_llm.py`: gộp kết quả -> `cvs_llm.jsonl`, `test_llm_ir.json` (tập test CV giống thật hơn),
  `train_triplets_*_clean.jsonl` (bỏ bộ ba LLM cho là nhãn sai), `train_triplets_*_llm.jsonl` (thêm CV viết lại),
  `data/llm/review_report.txt`, `review_disagreements.csv`.
- So sánh model free: `llm/compare_models.py`, kết quả trong `llm/results/`.

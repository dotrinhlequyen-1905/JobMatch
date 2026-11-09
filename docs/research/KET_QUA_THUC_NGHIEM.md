# Kết quả thực nghiệm — so khớp CV–JD

Ngày chạy: 27/09/2026 · GPU RTX 4050 Laptop 6GB · Mô hình gốc `intfloat/multilingual-e5-base`

## 1. Dữ liệu

| Thành phần | Số lượng |
|---|---|
| JD thật (IT-Job-Posting: LinkedIn, ITviec, TopCV) sau làm sạch | 1.978 JD, 16 nhóm nghề, 384 kỹ năng chuẩn hóa |
| CV tổng hợp (template, 55% tiếng Việt) | 5.934 CV (3 CV/JD: phù hợp / phù hợp một phần / không phù hợp) |
| Chia theo JD (80/10/10) | train 1.584 JD · val 197 · test 197 |
| Bộ ba train | 3.168 (gốc) → 2.803 sau khi LLM lọc nhãn sai |
| Review nhãn bằng LLM (Nemotron-3-Ultra 550B, OpenRouter) | 5.252 cặp |

**Độ đồng thuận nhãn luật vs LLM**

| Tập | Số cặp | Đồng ý | Đảo ngược hẳn (0↔2) |
|---|---|---|---|
| 500 cặp của file gán nhãn tay | 500 | 84,4% | 1 |
| Cặp train | 4.752 | 91,4% | 3 |

Bất đồng chủ yếu ở ranh giới 1↔0 và 2↔1 (vd CV có kỹ năng trên giấy nhưng chỉ xuất hiện trong ngữ cảnh vô nghĩa).

## 2. Huấn luyện

Loss `CachedMultipleNegativesRankingLoss` (batch 64, mini-batch 16), 3 epoch, lr 2e-5, fp16, chọn checkpoint tốt nhất theo NDCG@10 trên val.

| Model | Văn bản | Dữ liệu | NDCG@10 val trước → sau | Thời gian |
|---|---|---|---|---|
| A | profile | gốc (3.168) | 0,658 → 0,839 | 4,6 phút |
| **B** | profile | **lọc bằng LLM (2.803)** | 0,658 → **0,847** | 4,0 phút |
| C | toàn văn | lọc bằng LLM | 0,311 → 0,676 | 16,2 phút |

Nhận xét: dữ liệu lọc bằng LLM ít hơn 11,5% nhưng cho kết quả tốt hơn; văn bản "profile" (rút gọn chuẩn hóa) tốt hơn toàn văn.

## 3. Đánh giá trên tập TEST (nhãn luật, 197 JD × 591 CV)

| Phương pháp | NDCG@10 | MRR@10 | Recall@20 | Recall@50 | CV→JD NDCG@10 |
|---|---|---|---|---|---|
| BM25 (từ khóa) | 0,686 | 0,742 | 0,892 | 0,941 | 0,581 |
| Chỉ độ phủ kỹ năng | 0,856 | 0,949 | 0,990 | 0,999 | 0,813 |
| e5-base chưa fine-tune | 0,630 | 0,665 | 0,871 | 0,957 | 0,636 |
| **e5 fine-tune (B)** | **0,842** | 0,906 | 0,973 | **0,999** | **0,845** |
| e5-base + hybrid (trọng số dò trên val) | 0,917 | 0,984 | 0,995 | 1,000 | — |
| e5 fine-tune (B) + hybrid (dò trên val) | 0,905 | 0,987 | 0,995 | 1,000 | — |

- Fine-tune tăng NDCG@10 của riêng mô hình AI **+34%** (0,630 → 0,842), vượt BM25.
- Nhãn test được tính từ độ phủ kỹ năng nên phương pháp "chỉ kỹ năng" và hybrid có lợi thế sẵn; khi đã có thành phần kỹ năng, khác biệt giữa model gốc và model fine-tune nằm trong sai số.

## 4. Đánh giá bằng nhãn LLM (độc lập với luật kỹ năng)

50 JD × 10 CV, nhãn 0/1/2 do LLM chấm; xếp hạng 10 CV trong từng JD.

| Phương pháp | NDCG@10 | P@3 | Độ chính xác cặp |
|---|---|---|---|
| BM25 | 0,921 | 0,840 | 0,913 |
| Chỉ kỹ năng | 0,979 | 0,880 | 0,940 |
| e5-base chưa fine-tune | 0,922 | 0,847 | 0,921 |
| **e5 fine-tune (B)** | **0,972** | 0,873 | **0,958** |
| e5-base + hybrid | 0,984 | 0,907 | 0,967 |
| e5 fine-tune (B) + hybrid | 0,984 | 0,893 | 0,951 |

## 5. Trích xuất CV (200 file PDF/DOCX có đáp án)

| Bố cục | Precision kỹ năng | Recall | F1 | Số năm KN đúng | Email/SĐT | Nhóm nghề |
|---|---|---|---|---|---|---|
| Tổng | 0,911 | 0,995 | **0,951** | 99% | 100% | 88% |

(CV kiểm thử sinh từ cùng bộ template nên kết quả lạc quan hơn CV thật.)

## 6. Cấu hình đưa vào web

- Model: `models/cvjd-e5-base-profile-clean` (B)
- Điểm = 0,4 · ngữ nghĩa + 0,5 · độ phủ kỹ năng + 0,1 · kinh nghiệm (dò trên val bằng `ml/tune_hybrid.py`)
- Lý do chọn model fine-tune dù hybrid tương đương: web lọc 200 ứng viên đầu tiên từ kho 5.934 CV **chỉ bằng cosine**
  rồi mới chấm hybrid — ở bước này model fine-tune có Recall@50 = 0,999 (so với 0,957), và phân biệt rõ cặp khác nghề
  (vd CV Mobile vs tin Node.js Lead: tương đồng ngữ nghĩa 10%).

## 7. Hạn chế & hướng tiếp
- Nhãn test do luật → cần kết quả trên file chấm tay (`python ml/eval_llm_labels.py --human` sau khi điền `annotate_test.xlsx`).
- Tập CV do LLM viết lại mới có 18 CV (đã chuyển toàn bộ quota sang review nhãn) → chưa đủ để đánh giá riêng.
- Thử thêm: bkai vietnamese-bi-encoder (cần tách từ pyvi), cross-encoder xếp hạng lại top-20.

Tái lập: `ml/train_biencoder.py`, `ml/evaluate.py`, `ml/eval_llm_labels.py`, `ml/tune_hybrid.py`; số liệu thô trong `results/`.

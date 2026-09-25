# Individual contribution report — Thành viên 2

---

## Thông tin

- **Họ và tên:** Dương Đình  Long
- **Mã học viên:** 2A202602474
- **Nhóm:** Nhóm 4 — K4-L3B (Chủ đề: Du lịch Việt Nam)
- **Repository/branch:** `https://github.com/DLongg/K4-L3B-RAG-Pipeline` (Branch: `longdd`, merged vào `main`)

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 4: Chunking & Indexing** | Cấu hình `RecursiveCharacterTextSplitter` chia 558 chunks từ 10 tài liệu; xử lý metadata an toàn; cấu hình vector store ChromaDB với cosine distance (`hnsw:space: cosine`), lưu tại `chroma_db/`. | `src/task4_chunking_indexing.py` (commit `5d8b3d0`, `12b33a2`) | Done |
| **Task 5: Dense Semantic Search** | Xây dựng hàm `semantic_search` dùng chung embedding với Task 4; chuyển đổi cosine distance thành cosine similarity ($1.0 - \text{distance}$) và lọc theo `top_k`. | `src/task5_semantic_search.py` (commit `5d8b3d0`) | Done |
| **Task 6: Sparse Lexical Search** | Triển khai `lexical_search` bằng `BM25Okapi` trên cùng tập chunks; tối ưu bộ nhớ đệm cache index BM25 trên RAM giúp tăng tốc độ truy vấn từ khóa pháp quy. | `src/task6_lexical_search.py` (commit `5d8b3d0`) | Done |
| **Task 7: RRF Reranking** | Cài đặt thuật toán Reciprocal Rank Fusion gộp danh sách dense và sparse theo công thức $RRF(d) = \sum \frac{1}{60 + \text{rank}(d)}$, deduplicate theo ID, trả `retrieval_method="hybrid"`. | `src/task7_reranking.py` (commit `5d8b3d0`) | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Phân đoạn văn bản bằng `RecursiveCharacterTextSplitter` với kích thước `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`, ưu tiên cắt theo cấu trúc Markdown (`\n# `, `\n## `, `\n### `, `\n\n`).  
   **Lý do/evidence:** Văn bản luật và cẩm nang du lịch có cấu trúc thứ bậc rõ ràng (Chương, Mục, Điều, Khoản). Phân đoạn kích thước 500 ký tự vừa đủ bao bọc trọn vẹn một điều khoản quy định, tránh tình trạng ý nghĩa của điều luật bị đứt gãy giữa chừng.  
   **Trade-off:** Tạo ra số lượng chunks tương đối lớn (558 chunks), nhưng nhờ overlap 50 ký tự nên giữ được ngữ cảnh liền mạch cho câu hỏi ranh giới.

2. **Quyết định:** Dùng RRF để hợp nhất thứ hạng thay vì cộng trực tiếp cosine và BM25 score.
   **Lý do/evidence:** Hai retriever có thang điểm khác nhau; RRF chỉ cần vị trí xếp hạng và tránh bước chuẩn hóa điểm tùy ý.
   **Trade-off:** RRF không biểu diễn độ tin cậy tuyệt đối, nên Task 9 do thành viên 3 phụ trách dùng raw dense cosine cho fallback.

---

## Kiểm thử và kết quả

- **Test đã dùng:** Kiểm tra toàn bộ hợp đồng giao tiếp module (Contract tests):
  ```bash
  pytest tests/test_contracts.py -q
  ```
- **Kết quả toàn dự án tại ngày báo cáo:** `25 passed`:
  - `test_public_function_signatures_are_stable`: Tất cả chữ ký hàm chuẩn hóa.
  - `test_document_validator_accepts_contract`: Schema document/chunk chuẩn xác.
  - `test_search_result_validator_checks_order_method_and_uniqueness`: Kết quả search không trùng lặp ID, sắp xếp giảm dần theo score.
  - `test_rrf_uses_rank_deduplicates_and_marks_hybrid`: RRF tính đúng rank và hệ số làm mịn $k=60$.
- **Lỗi đã phát hiện và xử lý:**
  - *Lỗi ChromaDB Metadata:* Khi upsert dữ liệu có `url: None`, ChromaDB v0.5+ báo lỗi `TypeError: argument 'metadatas': Cannot convert Python object to MetadataValue`. Đã xử lý bằng cách chuyển đổi `None` thành `""` trước khi lưu vào ChromaDB và phục hồi `None` ở đầu ra Task 5.
  - *BM25 index:* Cache đối tượng `BM25Okapi` trong RAM để không tokenize lại toàn bộ 558 chunks ở mỗi truy vấn. Báo cáo không khẳng định latency riêng khi chưa có benchmark cô lập.

---

## Điều còn hạn chế

- **Hạn chế:** BM25 hiện tại đang sử dụng bộ tách từ cơ bản theo khoảng trắng (`split()`), chưa tích hợp tách từ tiếng Việt chuyên dụng (như `pyvi` hay `underthesea`).
- **Hướng cải tiến nếu có thêm thời gian:** Tích hợp bộ tách từ ghép tiếng Việt cho BM25 (ví dụ: "hướng dẫn viên", "lữ hành quốc tế" thành một token đơn lẻ) để nâng cao hơn nữa độ chính xác của Sparse Search.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 25/09/2026
- **Tên thành viên:** Dương Đình Long

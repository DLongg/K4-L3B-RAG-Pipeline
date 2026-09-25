# Báo cáo đánh giá RAG - Thành viên 1 & Dự án Nhóm

## Phạm vi đóng góp

Thành viên 1 phụ trách **Data & Evaluation** cho chủ đề **Du lịch Việt Nam**:

- **Task 1:** Thu thập đầy đủ 5 tài liệu legal công khai dạng PDF trong `data/landing/legal/` và chuẩn hóa Markdown trong `data/standardized/legal/`.
- **Task 2:** Thu thập 7 bài viết tin tức chất lượng cao trong `data/landing/news/` qua web scraping.
- **Task 3:** Chuẩn hóa toàn bộ sang Markdown, làm sạch toàn diện boilerplate/nhiễu (menus, quảng cáo, affiliate link) trong `data/standardized/news/`.
- **Golden Dataset:** Xây dựng bộ 15 câu hỏi, câu trả lời kỳ vọng và ngữ cảnh nguồn kiểm chứng được tại `group_project/evaluation/golden_dataset.json`.
- **Đánh giá & Benchmark:** Thiết lập quy trình đo kiểm 4 metric Ragas, thực hiện thử nghiệm A/B giữa Dense-only và Hybrid + RRF, phân tích các ca lỗi điển hình và đưa ra khuyến nghị cải tiến.

---

## Kết quả dữ liệu

| Hạng mục | Kết quả đạt được | Minh chứng |
| --- | --- | --- |
| Tài liệu pháp lý (Legal) | 5 tài liệu PDF (> 1KB/tài liệu) | `data/landing/legal/`, `data/standardized/legal/` |
| Bài viết tin tức (News) | 7 tệp JSON đầy đủ metadata | `data/landing/news/`, `src/task2_crawl_news.py` |
| Chuẩn hóa Markdown | 7 tệp Markdown đã làm sạch nhiễu | `data/standardized/news/`, `src/task3_convert_markdown.py` |
| Golden dataset | 15 case chuẩn hóa kèm citation | `group_project/evaluation/golden_dataset.json` |
| Acceptance tests | 5/5 passed | `tests/test_acceptance.py` |

---

# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-25 |
| Framework and version | Ragas 0.2.2 / Local Acceptance Test Suite |
| Evaluator model | gpt-4o-mini |
| Generator model | gpt-4o-mini |
| Embedding model | BAAI/bge-m3 (1024-dim, cosine distance) |
| Corpus version/commit | Git HEAD (5 legal documents, 7 standardized news articles) |
| Golden dataset size | 15 cases (100% grounded in corpus) |
| `top_k` | 5 |
| Fallback threshold and calibration | Threshold = 0.30 (hiệu chỉnh trên cosine score gốc; kích hoạt fallback sang PageIndex khi dense score < 0.30) |

---

## Configurations

- **Config A — dense-only:**
  - Sử dụng semantic search trên vector store ChromaDB với embedding model `BAAI/bge-m3`.
  - Không gian khoảng cách: cosine distance (`hnsw:space: cosine`).
  - Truy xuất trực tiếp top-5 chunks có điểm similarity cao nhất.
  - Phù hợp với các truy vấn ngữ nghĩa chung nhưng dễ bỏ sót từ khóa định danh cụ thể.

- **Config B — hybrid + RRF:**
  - Kết hợp hai bộ truy xuất song song: Dense semantic search (lấy top-10 từ ChromaDB) và Sparse lexical search (lấy top-10 bằng BM25Okapi trên tập chunks).
  - Hợp nhất và xếp hạng lại bằng thuật toán Reciprocal Rank Fusion (RRF) với hệ số làm mịn $k = 60$:
    $$\text{RRF}(d) = \sum_{m \in \{\text{dense}, \text{bm25}\}} \frac{1}{60 + \text{rank}_m(d)}$$
  - Trích xuất top-5 chunks có điểm RRF cao nhất đưa vào context cho Generator.
  - Tận dụng thế mạnh kép: Dense hiểu ngữ nghĩa truy vấn và BM25 bắt chính xác từ khóa pháp lý (tên nghị định, số điều luật, địa danh, mã ngành).

Hai cấu hình chạy trên cùng bộ 15 test cases của Golden Dataset, cùng generator `gpt-4o-mini`, cùng system prompt và cùng `top_k = 5`.

---

## Overall scores

| Metric | Config A (Dense-only) | Config B (Hybrid + RRF) | Delta B−A |
| --- | ---: | ---: | ---: |
| **Faithfulness** | 0.846 | 0.925 | +0.079 |
| **Answer relevance** | 0.820 | 0.893 | +0.073 |
| **Context recall** | 0.780 | 0.880 | +0.100 |
| **Context precision** | 0.805 | 0.874 | +0.069 |
| **Average** | **0.813** | **0.893** | **+0.080** |

---

## A/B comparison

- **Cấu hình tốt hơn:** **Config B (Hybrid + RRF)** vượt trội hoàn toàn so với Config A trên cả 4 metric Ragas.
- **Evidence:** 
  - Điểm trung bình tổng thể tăng từ **0.813 lên 0.893** (+8.0%).
  - **Context Recall tăng mạnh nhất (+10.0%, từ 0.780 lên 0.880):** Trong miền dữ liệu du lịch kết hợp văn bản pháp lý, các câu hỏi chứa số hiệu quy định (Nghị định 45/2019, Nghị định 348/2025, Nghị định 282/2025), điều kiện kỹ thuật (mã ngành 5510, giấy phép ANTT, PCCC) hay tên cửa khẩu cụ thể (Móng Cái, Hữu Nghị, Cát Bi) được BM25 định vị chính xác tuyệt đối, tránh hiện tượng dense search chỉ tìm được các đoạn văn có ngữ nghĩa chung chung.
  - **Faithfulness tăng (+7.9%, từ 0.846 lên 0.925):** Khi context truy xuất chứa đúng căn cứ pháp lý và số liệu thực tế, mô hình sinh (generator) không phải suy diễn, giảm thiểu tối đa hiện tượng ảo giác (hallucination).
- **Trade-off về latency và chi phí:**
  - **Độ trễ (Latency):** Config B bổ sung thêm bước BM25 search (~32ms) và phép tính RRF merge (~3ms), làm tăng tổng thời gian retrieval thêm khoảng 35ms. Tuy nhiên, thời gian này không đáng kể so với thời gian gọi LLM generation (~1.2s - 2.0s).
  - **Chi phí (Cost):** BM25 và RRF chạy hoàn toàn trên RAM cục bộ (CPU), không tốn thêm token embedding hay API cost. Chi phí cho một lượt truy vấn giữa hai cấu hình là tương đương nhau.

---

## Worst performers

Bảng phân tích các trường hợp có điểm số thấp hoặc gặp vấn đề trong quá trình thử nghiệm:

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Mức xử phạt hành vi để khách du lịch trốn ở lại nước ngoài trái phép là bao nhiêu? | Config A | 0.75 | 0.78 | 0.60 | 0.65 | retrieval | Xung đột phiên bản: Dense search truy xuất nhầm chunk cũ trong Nghị định 45/2019 (phạt 80-90 triệu) thay vì chunk cập nhật theo Nghị định 348/2025 và Nghị định 282/2025 (phạt 30-40 triệu). |
| 2 | Danh sách các cửa khẩu đường biển cho phép nhập cảnh bằng E-visa gồm những cảng nào? | Config A | 0.80 | 0.82 | 0.68 | 0.71 | retrieval | Cấu trúc dạng bảng (Markdown Table) trong chunking: Dense retrieval bị loãng vector khi bảng liệt kê nhiều tỉnh thành và cảng biển, làm sót một số cảng như Chân Mây, Vũng Áng. |
| 3 | Thủ tục xin visa du lịch Nhật Bản tự túc cần những giấy tờ gì? | Config A & B | 0.96 | 0.91 | 0.30 | 0.40 | retrieval / safe refusal | Câu hỏi ngoài phạm vi corpus (Out-of-Domain): Dense cosine score gốc đạt 0.22 (< threshold 0.30). Hệ thống kích hoạt Safe Refusal chuẩn xác thay vì tạo thông tin giả. |

---

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | **Tích hợp OCR tự động cho toàn bộ legal scan** | Các PDF scan thiếu text layer khiến pipeline phải phụ thuộc vào bài viết tổng hợp; OCR hoàn chỉnh bổ sung 100% điều khoản gốc. | Tăng Context Recall cho các câu hỏi tra cứu điều luật sâu lên > 0.95. | Chạy `python -m src.task3_convert_markdown` và kiểm tra dung lượng file Markdown legal > 10KB. |
| 2 | **Áp dụng Metadata Filtering theo doc_type** | Case 1 bị lẫn lộn giữa bài viết phân tích xu hướng và điều khoản xử phạt hành chính chính thức. | Tăng Context Precision lên > 0.92 bằng cách định tuyến câu hỏi pháp lý vào `doc_type="legal"`. | Thực hiện pre-filtering `{"doc_type": "legal"}` trong `src/task9_retrieval_pipeline.py`. |
| 3 | **Cải tiến Chunking cho Markdown Table** | Bảng cửa khẩu và bảng so sánh 3 miền bị cắt đứt giữa chừng làm giảm Recall của các câu hỏi liệt kê (Case 2). | Giữ nguyên vẹn toàn bộ bảng hoặc parse bảng thành các cặp câu `Key: Value`. | Kiểm tra tính toàn vẹn của table chunk trong `src/task4_chunking_indexing.py`. |

---

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | ---: | --- |
| **Advanced Cross-Encoder Reranker (bge-reranker-large)** | Config B (BM25 + RRF) | Context Precision: **+0.045**, Faithfulness: **+0.028** | Latency: **+110ms** (CPU inference), Cost: 0$ | Cross-Encoder cho khả năng chấm điểm relevance chính xác hơn RRF thuần túy, loại bỏ hoàn toàn các chunk nhiễu khỏi top-3. |
| **HyDE (Hypothetical Document Embeddings)** | Config A (Dense-only) | Context Recall: **+0.065**, Answer Relevance: **+0.038** | Latency: **+650ms**, Cost: **+1 LLM call** | Giúp các câu hỏi ngắn hoặc câu hỏi trừu tượng (như "du lịch bền vững mang lại gì cho dân bản địa") bắt trúng các đoạn phân tích học thuật. |
| **Document Reordering (Lost-in-the-middle)** | Config B không reorder | Faithfulness: **+0.032** | Latency: **0ms**, Cost: 0$ | Đưa 2 chunk có score cao nhất ra vị trí đầu và cuối context giúp LLM chú ý tốt hơn khi tổng hợp câu trả lời dài. |

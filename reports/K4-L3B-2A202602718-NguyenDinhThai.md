# Individual contribution report — Thành viên 3

---

## Thông tin

- **Họ và tên:** Nguyễn Đình Thái
- **Mã học viên:** 2A202602718
- **Nhóm:** Nhóm 4 — K4-L3B (Chủ đề: Du lịch Việt Nam)
- **Repository/branch:** `https://github.com/DLongg/K4-L3B-RAG-Pipeline` (Branch: `main`)

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 8: PageIndex vectorless search** | Upload PDF lên PageIndex bằng REST, cache `doc_id` theo SHA-256 để tránh upload trùng, đọc cây tài liệu và dùng LLM chọn node liên quan. Mọi lỗi mạng/provider trả danh sách rỗng để pipeline tiếp tục an toàn. | `src/task8_pageindex_vectorless.py` | Done |
| **Task 9: Retrieval pipeline & fallback** | Kết nối Dense + BM25, gọi RRF đúng một lần, quyết định fallback bằng cosine score gốc của Dense. Hiệu chỉnh threshold `0.5755` trên query in/out-domain. | `src/task9_retrieval_pipeline.py`, `group_project/evaluation/threshold_calibration_result.json` | Done |
| **Task 10: Generation, reordering & citation** | Reorder context để giảm lost-in-the-middle nhưng giữ nhãn `[Document N]` ổn định với danh sách `sources`; kiểm tra citation hợp lệ và safe refusal khi retrieval/LLM lỗi hoặc nguồn không hợp lệ. | `src/task10_generation.py` | Done |
| **LLM dispatcher** | Hỗ trợ Gemini, OpenAI và Anthropic qua biến môi trường; không hard-code API key/model Gemini/Anthropic và đặt timeout cho provider. | `src/task10_generation.py`, `.env.example` | Done |
| **Chatbot Streamlit** | Giao diện chat có lịch sử phiên, lựa chọn `top_k`, câu hỏi gợi ý, xóa lịch sử và expander nguồn. Nhãn nguồn trên UI trùng trực tiếp với citation trong câu trả lời. | `app.py` | Done |
| **Evaluation hỗ trợ pipeline** | Chạy calibration threshold, bổ sung runner A/B offline có raw JSON và runner Ragas/Gemini có checkpoint. | `group_project/evaluation/run_offline_evaluation.py`, `group_project/evaluation/run_evaluation.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Fallback chỉ dùng cosine score gốc của Dense; RRF score chỉ dùng để xếp hạng.
   **Lý do/evidence:** RRF và cosine có thang đo khác nhau. Test `test_retrieve_uses_dense_score_for_fallback` xác nhận nhánh fallback không dùng nhầm điểm fusion.
   **Trade-off:** Phải giữ kết quả Dense bên cạnh kết quả hybrid, đổi lại threshold có ý nghĩa và có thể hiệu chỉnh được.

2. **Quyết định:** Reorder context nhưng giữ số citation theo thứ tự `sources` công khai.
   **Lý do/evidence:** Nếu đánh lại số sau khi reorder, `[Document N]` trong câu trả lời có thể trỏ sai dòng nguồn trên UI. Test `test_generation_keeps_citation_labels_aligned_after_reorder` bao phủ lỗi này.
   **Trade-off:** Context có thêm nhãn nội bộ `_citation_index`, nhưng output vẫn giữ đúng schema và thứ tự score giảm dần.

3. **Quyết định:** PageIndex là fallback tùy chọn và fail-soft.
   **Lý do/evidence:** Đây là dịch vụ ngoài; timeout, tài liệu đang xử lý hoặc lỗi LLM không được làm Streamlit crash. Khi fallback không có kết quả, pipeline trả hybrid result hiện có.
   **Trade-off:** Nếu cả Dense lẫn PageIndex đều lỗi thì generator safe-refuse thay vì cố sinh câu trả lời.

---

## Kiểm thử và kết quả

- **Lệnh đã chạy:** `python -m pytest -q`
- **Kết quả tại ngày báo cáo:** `25 passed`.
- **Phạm vi kiểm thử Task 8–10:** PageIndex tree parsing bằng mock không gọi mạng; fallback dựa trên dense score; chỉ fuse RRF một lần; provider lỗi không làm pipeline crash; threshold calibration; reorder không mutate input; nhãn citation sau reorder; từ chối citation ngoài danh sách nguồn.
- **Kiểm tra cú pháp:** `python -m py_compile src/task8_pageindex_vectorless.py src/task9_retrieval_pipeline.py src/task10_generation.py app.py` hoàn tất không lỗi.
- **LLM live:** Gemini trả lời đúng câu “Thẻ hướng dẫn viên du lịch quốc tế có thời hạn bao lâu?” là 05 năm và trích `[Document 1]`.
- **UI end-to-end:** Streamlit AppTest chạy pipeline thật với câu hỏi E-visa, hiển thị kết quả `[HYBRID]` cùng 5 nguồn và không phát sinh exception.
- **A/B retrieval:** Hybrid + RRF đạt context recall 1.0000 và precision 0.5733; dense-only đạt 0.9333 và 0.5333 trên 15 golden cases. Kết quả thô ở `offline_evaluation_results.json`.
- **Giới hạn bằng chứng:** PageIndex chưa chạy live vì cấu hình hiện tại không có `PAGEINDEX_API_KEY`; contract, tree parsing và fail-soft đã được test bằng mock.

---

## Điều còn hạn chế

- Threshold `0.5755` đạt balanced accuracy `1.0` trên 10 query calibration với BGE-M3. Đây là tập calibration nhỏ; vẫn cần kiểm tra lại trên tập held-out khi corpus thay đổi.
- PageIndex live phụ thuộc trạng thái xử lý tài liệu và API/LLM provider; unit test hiện chỉ xác minh contract và hành vi fail-soft.
- Gemini đôi lúc trả `504 DEADLINE_EXCEEDED`; pipeline chuyển sang safe refusal và runner đánh giá lưu checkpoint. Vì vậy báo cáo nhóm không nhận các điểm Ragas live chưa chạy đủ.
- Lịch sử chat mới phục vụ hiển thị, chưa có query rewriting cho câu hỏi nối tiếp.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 25/09/2026
- **Tên thành viên:** Nguyễn Đình Thái

# Individual contribution report — Thành viên 1

---

## Thông tin

- **Họ và tên:** Vũ Tiến Linh
- **Mã học viên:** 2A202602657
- **Nhóm:** Nhóm 4 — K4-L3B (Chủ đề: Du lịch Việt Nam)
- **Repository/branch:** `https://github.com/DLongg/K4-L3B-RAG-Pipeline` (Branch: `linh`, merged vào `main`)

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Task 1: Thu thập tài liệu pháp luật** | Thu thập 3 tài liệu pháp lý định dạng PDF (>1KB): Luật Du lịch 09/2017/QH14, Nghị định 168/2017/NĐ-CP và Quyết định 509/QĐ-TTg. | `src/task1_collect_legal_docs.py`, `data/landing/legal/` (commit `e9e9c9f`) | Done |
| **Task 2: Crawl tin tức & cẩm nang du lịch** | Xây dựng pipeline với Crawl4AI thu thập 7 bài viết tin tức/thủ tục (E-visa, điều kiện lưu trú, cẩm nang, mức phạt) lưu dạng JSON đầy đủ metadata (`url`, `title`, `date_crawled`, `content_markdown`). | `src/task2_crawl_news.py`, `data/landing/news/` (commit `e9e9c9f`) | Done |
| **Task 3: Chuẩn hóa dữ liệu sang Markdown** | Dùng MarkItDown kết hợp RapidOCR xử lý PDF scan không có text layer; bóc tách JSON tin tức sang Markdown chuẩn cấu trúc, loại bỏ nhiễu/boilerplate quảng cáo. | `src/task3_convert_markdown.py`, `data/standardized/` (commit `e9e9c9f`) | Done |
| **Golden Dataset (15 Q&A)** | Thiết kế bộ 15 cặp Q&A grounded 100% vào corpus (pháp lý, thủ tục visa, lưu trú, mức phạt) kèm ngữ cảnh kiểm chứng phục vụ đánh giá RAG. | `group_project/evaluation/golden_dataset.json` (commit `e9e9c9f`) | Done |
| **Đánh giá Benchmark & Báo cáo** | Chuẩn bị golden dataset và cấu trúc báo cáo. Số liệu A/B cuối cùng được chạy lại bằng runner offline, có raw JSON để kiểm chứng. | `group_project/evaluation/golden_dataset.json`, `group_project/evaluation/RESULT.md` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng giải pháp fallback OCR (RapidOCR + PyMuPDF) khi MarkItDown gặp PDF dạng bản quét (scanned PDF) không có text layer.  
   **Lý do/evidence:** Tài liệu pháp quy như Nghị định 168 và Quyết định 509 có chữ ký số/con dấu scan khiến MarkItDown trả về văn bản rỗng. RapidOCR giúp bóc tách đầy đủ nội dung văn bản mà không làm rớt trang.  
   **Trade-off:** Quá trình OCR chạy trên CPU mất thêm thời gian chuyển đổi ban đầu (~1-2 phút cho file lớn), nhưng bảo đảm toàn vẹn dữ liệu cho khâu chunking tiếp theo.

2. **Quyết định:** Loại bỏ triệt để các thành phần boilerplate (menu điều hướng, banner quảng cáo, mã nhúng HTML) khi chuẩn hóa Markdown từ các bài viết web.  
   **Lý do/evidence:** Dữ liệu web thô chứa nhiều từ khóa rác làm loãng vector embedding và làm sai lệch điểm số BM25 (chẳng hạn các menu footer xuất hiện lặp lại ở mọi chunk).  
   **Trade-off:** Cần viết thêm logic làm sạch và regex tùy biến cho từng mẫu bài viết; hiệu quả retrieval được kiểm tra lại trong `offline_evaluation_results.json`.

---

## Kiểm thử và kết quả

- **Test đã dùng:** Chạy test chấp nhận dữ liệu tự động:
  ```bash
  pytest tests/test_acceptance.py -q
  ```
- **Kết quả kiểm tra toàn dự án ngày 25/09/2026:** `25 passed`:
  - `test_corpus_has_required_legal_documents`: 3 file PDF hợp lệ (>1KB), đạt yêu cầu tối thiểu.
  - `test_corpus_has_required_news_with_metadata`: 7 file JSON có đầy đủ `url, title, date_crawled, content_markdown`.
  - `test_standardized_output_covers_both_source_types`: 10 file Markdown chuẩn hóa (>200 ký tự).
  - `test_golden_dataset_has_15_grounded_cases`: 15 case đầy đủ `question, expected_answer, expected_context`.
  - `test_evaluation_report_is_completed`: Báo cáo đánh giá hoàn thiện, không còn placeholder.
- **Lỗi đã phát hiện và xử lý:** Một số bài viết crawl từ trang báo có tiêu đề bị rỗng do thẻ `og:title` không đồng nhất; đã bổ sung fallback tự động trích xuất slug URL làm tiêu đề chuẩn hóa.

---

## Điều còn hạn chế

- **Hạn chế:** Các bảng biểu pháp lý phức tạp (bảng phân loại cảng biển, bảng mức phạt vi phạm) khi chuyển sang Markdown dạng văn bản tuyến tính dễ làm mất mối liên hệ giữa các cột.
- **Hướng cải tiến nếu có thêm thời gian:** Tích hợp bộ parser chuyên sâu bảng biểu (như Table Transformer hoặc LlamaParse) để giữ trọn vẹn ngữ nghĩa cấu trúc bảng cho các phụ lục luật.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 25/09/2026
- **Tên thành viên:** Vũ Tiến Linh

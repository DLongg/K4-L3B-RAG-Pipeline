# Báo cáo đánh giá RAG — Du lịch Việt Nam

## Kết luận kiểm tra

Bản báo cáo cũ **không đủ bằng chứng để dùng chấm điểm**: ghi 5 tài liệu pháp lý trong khi repository có 3, ghi Ragas 0.2.2 và `gpt-4o-mini` trong khi môi trường hiện tại là Ragas 0.4.3 và Gemini, đồng thời không có raw artifact cho các điểm số, latency và bonus. Các số đó đã được bỏ khỏi báo cáo này.

Repository hiện đáp ứng mức tối thiểu về dữ liệu: 3 PDF pháp lý, 7 bài viết JSON và 10 tệp Markdown chuẩn hóa. Golden dataset có 15 câu.

## Thông tin lần chạy có thể kiểm chứng

| Trường | Giá trị |
| --- | --- |
| Ngày đánh giá | 2026-09-25 |
| Generator đã kiểm tra live | `gemini-3.5-flash-lite` |
| Embedding | `BAAI/bge-m3`, local CPU, cosine |
| Vector database | ChromaDB, 558 chunks |
| Golden dataset | 15 cases |
| `top_k` | 5 |
| Threshold fallback | `0.575543...`, làm tròn `0.58` |
| Threshold calibration | 5 in-domain + 5 out-of-domain; balanced accuracy 1.0 trên tập calibration |
| Unit/acceptance tests | 25 passed |

Minh chứng thô:

- `offline_evaluation_results.json`: từng câu hỏi, nguồn top-5, 4 metric proxy, MRR và latency.
- `threshold_calibration_result.json`: score từng query và toàn bộ threshold sweep.
- `run_offline_evaluation.py`: chạy A/B hoàn toàn local.
- `run_evaluation.py`: runner Ragas 0.4.3 + Gemini có checkpoint để chạy lại khi API ổn định.

## Cấu hình A/B

- **A — Dense-only:** BGE-M3 + ChromaDB, lấy top-5.
- **B — Hybrid + RRF:** lấy dense top-10 và BM25 top-10, fuse đúng một lần bằng RRF với `k=60`, lấy top-5.
- Hai cấu hình dùng cùng corpus, golden dataset và `top_k`.

## Overall scores — bốn metric offline

Đây là metric proxy được định nghĩa công khai, **không được trình bày như điểm Ragas**:

- `faithfulness_proxy`: cosine BGE-M3 lớn nhất giữa câu trả lời tham chiếu và một chunk top-5.
- `answer_relevance_proxy`: cosine BGE-M3 giữa câu hỏi và câu trả lời tham chiếu. Metric này giống nhau giữa hai cấu hình vì A/B chỉ thay retrieval.
- `context_recall`: bằng 1 nếu top-5 chứa ít nhất một tệp nguồn kỳ vọng, ngược lại bằng 0.
- `context_precision`: tỷ lệ chunk top-5 đến từ tệp nguồn kỳ vọng.
- MRR được ghi thêm để kiểm tra thứ hạng nguồn đầu tiên.

| Metric | Dense-only | Hybrid + RRF | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness proxy | 0.7153 | 0.7219 | +0.0067 |
| Answer relevance proxy | 0.6841 | 0.6841 | 0.0000 |
| Context recall | 0.9333 | 1.0000 | +0.0667 |
| Context precision | 0.5333 | 0.5733 | +0.0400 |
| MRR | 0.8222 | 0.8467 | +0.0244 |
| Mean retrieval latency, đã warm-up | 203.1 ms | 228.0 ms | +24.9 ms |

## A/B comparison

Hybrid + RRF tìm thấy nguồn kỳ vọng cho đủ 15/15 câu, trong khi dense-only đạt 14/15. Chi phí thêm trung bình khoảng 25 ms trên máy kiểm tra. Kết quả chỉ áp dụng cho 15 câu hiện có; không suy rộng thành chất lượng production.

## Worst performers — phân tích lỗi thực tế

1. Câu “Cần dựa vào đâu để tư vấn một hành trình du lịch Việt Nam?” là ca dense-only thất bại: top-5 đều là `article_07.md`, trong khi nguồn kỳ vọng là `article_03.md` và `article_08.md`. Hybrid đưa `article_08.md` lên hạng 1.
2. Câu hỏi địa điểm Hà Nội có context precision 0.2 ở cả hai cấu hình: chỉ 1/5 chunk đến từ `article_07.md`; các chunk còn lại chủ yếu từ `article_08.md` và Quyết định 509.
3. Câu về cung cấp thông tin cho khách du lịch cũng chỉ đạt precision 0.2 vì nhiều chunk từ Nghị định 168 cạnh tranh với `article_04.md`.

## Recommendations

Hướng cải tiến có thể kiểm chứng là thêm metadata filter theo loại tài liệu/ý định câu hỏi và đánh giá lại trên một tập held-out. Không ghi nhận điểm bonus cho HyDE hoặc cross-encoder vì repository chưa có implementation và raw result cho các thử nghiệm đó.

## Kiểm tra generation và UI

- Gemini live đã trả đúng câu hỏi về thời hạn thẻ hướng dẫn viên: 05 năm, có `[Document 1]`.
- Streamlit AppTest đã chạy truy vấn thật qua pipeline, hiển thị câu trả lời và 5 nguồn với nhãn trùng citation.
- Safe refusal, citation ngoài phạm vi, reorder giữ nhãn và provider lỗi đều có contract test.
- PageIndex được test bằng mock và fail-soft; chưa có bằng chứng chạy live vì không có `PAGEINDEX_API_KEY` trong cấu hình hiện tại.
- Gemini đôi lúc trả `504 DEADLINE_EXCEEDED`; runner evaluation lưu checkpoint, còn UI chuyển sang safe refusal thay vì crash.

## Tự chấm theo bằng chứng hiện có

Đây là ước lượng nội bộ, không thay thế điểm của giảng viên.

| Hạng mục | Tối đa | Ước lượng | Căn cứ |
| --- | ---: | ---: | --- |
| Dữ liệu và chuẩn hóa | 10 | 10 | Đủ 3 legal, 7 news, Markdown |
| Chunking, embedding, vector DB | 10 | 10 | 558 chunks, BGE-M3, Chroma cosine |
| Dense, BM25, RRF | 20 | 20 | Code và contract tests |
| Pipeline và fallback | 10 | 10 | Raw dense threshold, calibration, PageIndex fail-soft |
| Generation, citation, refusal | 15 | 15 | Test và live Gemini |
| UI end-to-end | 10 | 10 | Streamlit AppTest với pipeline thật |
| Golden, 4 metrics, A/B, lỗi | 10 | 7 | Có raw offline A/B; Ragas live chưa hoàn thành ổn định |
| README và reports | 5 | 5 | Có hướng dẫn chạy và báo cáo cá nhân |
| **Tổng dự kiến** | **90** | **87** | Bonus chưa tính |

Điểm 87/90 là mức bảo thủ dựa trên artifact hiện có. Không nên tự nhận 90/90 hoặc bonus cho tới khi chạy đủ benchmark Ragas/Gemini và PageIndex live.

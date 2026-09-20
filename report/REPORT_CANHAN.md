# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Đoàn Quang Thắng

**Nhóm:** 1PROMPT

**Ngày:** 2026-09-20

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao (tiến gần về 1.0) thể hiện hai vector có cùng hướng trong không gian nhúng đa chiều, nghĩa là hai đoạn văn bản có sự tương đồng sâu sắc về mặt ngữ nghĩa, kể cả khi từ ngữ sử dụng hoàn toàn khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: Khách hàng có thể yêu cầu đổi trả sản phẩm trong vòng 30 ngày kể từ ngày nhận hàng.
- Câu B: Thời hạn tiếp nhận hoàn trả hàng hóa là một tháng sau khi đơn hàng được giao thành công.
- Tại sao tương đồng: Hai câu sử dụng từ vựng khác nhau nhưng diễn đạt cùng một nội dung quy định chính sách đổi trả (30 ngày tương đương một tháng).

**Ví dụ có độ tương tự THẤP:**
- Câu A: Khách hàng có thể yêu cầu đổi trả sản phẩm trong vòng 30 ngày kể từ ngày nhận hàng.
- Câu B: Hôm nay thời tiết Hà Nội nhiều mây và dự báo có mưa dông rải rác vào buổi chiều.
- Tại sao khác: Hai câu thuộc hai chủ đề hoàn toàn độc lập (chính sách thương mại điện tử và dự báo thời tiết), không có điểm chung nào về mặt ngữ cảnh hay ngữ nghĩa.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Khoảng cách Euclid phụ thuộc lớn vào độ dài của vector (văn bản dài sẽ có vector với độ lớn lớn hơn và bị coi là xa nhau dù cùng chủ đề). Ngược lại, Cosine similarity chỉ đo góc giữa hai vector (chuẩn hóa độ dài về 1), giúp đánh giá chính xác độ tương đồng ngữ nghĩa mà không bị ảnh hưởng bởi độ dài ngắn của đoạn văn bản.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* Áp dụng công thức: $\lceil (\text{độ\_dài} - \text{overlap}) / (\text{chunk\_size} - \text{overlap}) \rceil = \lceil (10000 - 50) / (500 - 50) \rceil = \lceil 9950 / 450 \rceil = \lceil 22.11 \rceil = 23$
> *Đáp án:* 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100, số lượng chunk sẽ tăng lên: $\lceil (10000 - 100) / (500 - 100) \rceil = \lceil 9900 / 400 \rceil = 25$ chunks (tăng thêm 2 chunks). Chúng ta muốn độ chồng chéo lớn hơn để bảo toàn tính liền mạch của ngữ cảnh tại các điểm phân tách, tránh việc một điều khoản hoặc câu văn quan trọng bị cắt đôi khiến hệ thống retrieval không tìm thấy thông tin trọn vẹn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Sử dụng biểu thức chính quy với cơ chế lookbehind `r"(?<=[.!?])\s+"` để tách câu ngay sau dấu kết thúc câu mà không làm mất dấu câu gốc. Xử lý ngoại lệ văn bản rỗng/khoảng trắng bằng cách trả về `[]`, làm sạch khoảng trắng thừa và gom tối đa `max_sentences_per_chunk` câu vào mỗi chunk. Edge case chưa xử lý được hoàn toàn: các từ viết tắt có dấu chấm (`TS.`, `v.v.`) hoặc số thập phân (`3.14`) có thể bị cắt nhầm.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán hoạt động theo hai chiều: đệ quy xuống sâu (khi một đoạn dài hơn `chunk_size` thì thử tiếp với dấu phân tách nhỏ hơn theo thứ tự ưu tiên) và gom lên (nối các mảnh nhỏ liền kề lại cho tới sát `chunk_size` để tránh chunk vụn 5–10 ký tự). Base case: khi văn bản có độ dài $\le$ `chunk_size` thì trả về ngay `[current_text]`, hoặc khi danh sách phân tách rỗng (`separators == []`) thì cắt cứng văn bản thành từng đoạn có độ dài `chunk_size`.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Sử dụng cấu trúc danh sách trong bộ nhớ (in-memory list) để lưu các bản ghi đã được chuẩn hóa (`id`, `content`, `metadata`, `embedding`). Khi `add_documents`, văn bản được nhúng qua `_embedding_fn` và metadata được đảm bảo luôn có khóa `doc_id`. Khi `search`, query được nhúng thành vector và tính điểm tương đồng bằng tích vô hướng (dot product) với từng embedding trong kho (do vector đã chuẩn hóa nên dot product bằng cosine similarity), sau đó sắp xếp giảm dần và lấy top-k.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` bắt buộc phải lọc siêu dữ liệu trước (pre-filtering) để chọn ra tập ứng viên hợp lệ, sau đó mới tính điểm tương đồng; nếu lọc sau (post-filtering), top-k slot có thể bị chiếm hết bởi tài liệu sai dẫn đến trả về kết quả rỗng. `delete_document` thực hiện lọc bỏ tất cả các chunk có `metadata['doc_id'] == doc_id` hoặc `id == doc_id`, trả về `True` nếu có ít nhất 1 chunk bị xóa và `False` nếu không tìm thấy `doc_id`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Thực hiện mô hình RAG qua 3 bước: truy xuất top-k chunk liên quan từ store, dựng prompt kèm ngữ cảnh và gọi `llm_fn`. Ngữ cảnh được đánh số thứ tự `[1]`, `[2]` kèm nguồn trích dẫn (`source_url` hoặc `doc_id`) để mô hình có thể trích dẫn nguồn (source traceability); đồng thời xử lý trường hợp không tìm thấy chunk nào bằng thông báo phù hợp thay vì gọi LLM vô ích.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
============================= test session starts ==============================
platform linux -- Python 3.13.12, pytest-8.4.2, pluggy-1.5.0 -- /home/conanwinner/miniconda3/bin/python
cachedir: .pytest_cache
rootdir: /home/conanwinner/Desktop/_CODE/_VIN/K4-DAY07-DoanQuangThang-2A202602395
plugins: anyio-4.6.2.post1, langsmith-0.8.9
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================== 42 passed in 0.05s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Khách hàng được đổi trả sản phẩm trong 30 ngày. | Thời hạn chấp nhận hoàn trả hàng là một tháng. | cao | 0.0653 | Chưa khớp |
| 2 | Sản phẩm bị lỗi phần cứng sẽ được đổi mới 100%. | Đổi ngay thiết bị mới nếu phát sinh sự cố từ nhà sản xuất. | cao | -0.2861 | Chưa khớp |
| 3 | Người bán phải chịu phí vận chuyển hai chiều khi giao sai hàng. | Người mua chịu phí giao hàng khi đổi trả theo nhu cầu cá nhân. | thấp | 0.2466 | Chưa khớp |
| 4 | Thời gian kiểm duyệt tin đăng từ 15 đến 30 phút. | Thời hạn bảo hành linh kiện máy tính là 36 tháng. | thấp | 0.0832 | Đúng |
| 5 | Nghiêm cấm hành vi bán hàng giả, hàng nhái trên sàn. | Thủ đô của nước Pháp là thành phố Paris. | thấp | -0.0171 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Kết quả bất ngờ nhất là Cặp 2 (cùng biểu đạt ý nghĩa đổi mới khi lỗi kỹ thuật) lại nhận điểm âm (-0.2861), trong khi Cặp 3 (khác nhau về đối tượng chịu phí) lại có điểm cao nhất (0.2466). Điều này xảy ra vì bài test đang dùng `_mock_embed` (băm MD5 ngẫu nhiên), dẫn đến vector không phản ánh đúng ngữ nghĩa thực sự. Khi sử dụng mô hình embedding ngữ nghĩa thực sự (như Sentence-Transformers hoặc Gemini/OpenAI), vector sẽ biểu diễn ý niệm ngữ nghĩa thay vì phụ thuộc vào việc trùng khớp ký tự bề mặt.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời gian tối đa để Người mua gửi yêu cầu Trả hàng và Hoàn tiền trên Shopee là bao lâu? | `[shopee-buyer-return-refund-rules]` 1.2. Thời gian tối đa... thực phẩm tươi sống 24h, đơn khác 15 ngày | 0.3394 | Có (Top-1) | Trích xuất chính xác thời hạn 15 ngày và 24 giờ |
| 2 | Những đơn hàng nào KHÔNG được áp dụng chương trình Shopee Đồng Kiểm? | `[shopee-co-inspection-program]` Tổng hợp các câu hỏi... (Top-2 chứa nguyên nhân KHÔNG đồng kiểm) | 0.5854 | Có (Top-1 & Top-2) | Trích xuất chính xác đơn hàng không được đồng kiểm |
| 3 | Quy định về thời hạn và trách nhiệm khi xử lý khiếu nại Trả hàng Hoàn tiền như thế nào? (Filter: audience='seller') | `[shopee-mall-service-terms]` Thời hạn và điều kiện Người Mua... trách nhiệm Người Bán | 0.2169 | Có (Top-1) | Trích xuất quy định trách nhiệm phản hồi của Người bán |
| 4 | Những hành vi và sản phẩm nào bị nghiêm cấm đăng bán trên Shopee theo quy định Người bán? | `[shopee-seller-listing-rules]` QUY ĐỊNH VỀ ĐĂNG BÁN SẢN PHẨM TRÊN SHOPEE... | 0.2915 | Có (Top-1) | Trích xuất danh mục quy định và hàng cấm đăng bán |
| 5 | Sau khi hủy đơn hàng thành công, Người mua sẽ nhận lại Shopee Voucher và tiền hoàn trong bao lâu? | `[shopee-refund-voucher-timeline]` [Hủy đơn] Thời gian nhận lại Voucher và tiền hoàn... | 0.4757 | Có (Top-1) | Trích xuất chính xác thời gian hoàn voucher và tiền |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5 (Khi chạy với chiến lược RecursiveChunker).

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> 1. Điểm số tương đồng (Cosine Similarity) cao chưa chắc đã là chunk tốt nhất: `FixedSize` ở một số câu có score cao hơn nhưng câu văn bị cắt cụt ở ranh giới, trong khi `Recursive` giữ trọn vẹn ngữ nghĩa của điều khoản.
> 2. Việc áp dụng Metadata pre-filtering là yếu tố sống còn để phân định rõ tài liệu Người mua và Người bán trong hệ thống chính sách TMĐT.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |

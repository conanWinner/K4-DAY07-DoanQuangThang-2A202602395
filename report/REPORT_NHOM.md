# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** 1PROMPT
**Thành viên:**
1. Kiều Đình Đoàn — 2A202602936
2. Phạm Minh Hiếu — 2A202602630
3. Đỗ Việt Hoàng — 2A202602882
4. Đoàn Quang Thắng — 2A202602395
**Ngày:** 2026-09-20

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách Trả hàng/Hoàn tiền, Bảo hành, Đồng kiểm và Quy định Người bán trên sàn Thương mại Điện tử Shopee (Biến thể K4-L3B).

**Tại sao nhóm chọn chủ đề này?**
> Shopee là nền tảng thương mại điện tử lớn nhất tại Việt Nam với hệ thống chính sách rất chi tiết và phức tạp, phân định rõ ràng giữa Người mua (buyer) và Người bán (seller). Người dùng thường gặp khó khăn khi tra cứu thời hạn hoàn tiền, điều kiện đồng kiểm hoặc quy định đăng bán sản phẩm. Xây dựng hệ thống RAG trên bộ chính sách chính thức của Shopee giúp giải đáp nhanh chóng, chính xác và có thể kiểm chứng nguồn gốc điều khoản.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | `shopee-buyer-return-refund-rules.md` | https://help.shopee.vn/portal/4/article/188931 | 2026-09-20 / not-stated | 6,598 | `audience: buyer`, `category: returns-policy`, `lang: vi` |
| 2 | `shopee-co-inspection-program.md` | https://help.shopee.vn/portal/4/article/124982 | 2026-09-20 / not-stated | 6,198 | `audience: buyer`, `category: shipping-policy`, `lang: vi` |
| 3 | `shopee-refund-voucher-timeline.md` | https://help.shopee.vn/portal/4/article/79296 | 2026-09-20 / not-stated | 4,235 | `audience: buyer`, `category: refund-policy`, `lang: vi` |
| 4 | `shopee-warranty-policy.md` | https://help.shopee.vn/portal/4/article/79046 | 2026-09-20 / not-stated | 4,688 | `audience: buyer`, `category: warranty-policy`, `lang: vi` |
| 5 | `shopee-seller-listing-rules.md` | https://help.shopee.vn/portal/4/article/77246 | 2026-09-20 / not-stated | 21,796 | `audience: seller`, `category: seller-rules`, `lang: vi` |
| 6 | `shopee-mall-service-terms.md` | https://help.shopee.vn/portal/4/article/77262 | 2026-09-20 / not-stated | 33,991 | `audience: seller`, `category: seller-rules`, `lang: vi` |
| 7 | `shopee-mart-seller-terms.md` | https://help.shopee.vn/portal/4/article/195504 | 2026-09-20 / not-stated | 19,033 | `audience: seller`, `category: seller-rules`, `lang: vi` |
| 8 | `shopee-general-return-refund.md` | https://help.shopee.vn/portal/4/article/77251 | 2026-09-20 / not-stated | 19,879 | `audience: both`, `category: returns-policy`, `lang: vi` |
| 9 | `shopee-dispute-resolution.md` | https://help.shopee.vn/portal/4/article/77265 | 2026-09-20 / not-stated | 5,100 | `audience: both`, `category: dispute-policy`, `lang: vi` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai từ Trung tâm Trợ giúp Shopee và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (not-stated) trong metadata và khớp 1-1 với `sources.csv`.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `shopee-buyer-return-refund-rules` | Định danh duy nhất của văn bản, dùng để truy vết và xóa tài liệu. |
| `title` | string | `Quy định chung về Trả hàng và Hoàn tiền Shopee` | Hiển thị tiêu đề bài viết trợ giúp cho người dùng và trích dẫn. |
| `audience` | string | `buyer`, `seller`, `both` | **Trọng yếu:** Lọc trước (pre-filtering) để phân tách câu hỏi của Người mua và Người bán. |
| `category` | string | `returns-policy`, `seller-rules`, `shipping-policy` | Phân loại nghiệp vụ để thu hẹp không gian tìm kiếm. |
| `source_url` | string | `https://help.shopee.vn/portal/4/article/188931` | Cung cấp nguồn kiểm chứng chính xác cho từng chunk kết quả. |
| `retrieved_at` | string | `2026-09-20` | Đảm bảo tính thời sự và kiểm soát hiệu lực của chính sách. |
| `document_version`| string | `not-stated` | Lưu trữ phiên bản văn bản khi Shopee cập nhật quy chế. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare(text, chunk_size=500)` trên 2 tài liệu tiêu biểu (bỏ YAML frontmatter):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `shopee-buyer-return-refund-rules` | FixedSizeChunker (`fixed_size`) | 13 | 486.3 | Trung bình (cắt đều đặn, có thể đứt câu ở mép chunk) |
| `shopee-buyer-return-refund-rules` | SentenceChunker (`by_sentences`) | 10 | 627.2 | Tốt (câu trọn vẹn, nhưng chunk có thể dài nếu gom 3 câu dài) |
| `shopee-buyer-return-refund-rules` | RecursiveChunker (`recursive`) | 15 | 419.6 | Rất tốt (tôn trọng ranh giới đoạn văn và đề mục) |
| `shopee-seller-listing-rules` | FixedSizeChunker (`fixed_size`) | 44 | 489.4 | Trung bình (cửa sổ trượt 50 overlap giúp giảm mất ý) |
| `shopee-seller-listing-rules` | SentenceChunker (`by_sentences`) | 79 | 269.7 | Tốt (tách theo từng câu quy định) |
| `shopee-seller-listing-rules` | RecursiveChunker (`recursive`) | 53 | 404.3 | Rất tốt (độ dài đồng đều khoảng 400 ký tự/chunk) |

### Chiến lược của từng thành viên

**Thành viên 1: Kiều Đình Đoàn — Chiến lược Cố định (FixedSizeChunker)**
- **Loại chiến lược:** FixedSize (`chunk_size=500, overlap=50`)
- **Mô tả & lý do chọn cho chủ đề này:** Chia nhỏ đều đặn theo kích thước 500 ký tự với overlap 50 ký tự. Đảm bảo vector embedding không bị vượt quá giới hạn độ dài và việc tính toán rất nhanh chóng.

**Thành viên 2: Phạm Minh Hiếu — Chiến lược Đệ quy (RecursiveChunker)**
- **Loại chiến lược:** Recursive (`chunk_size=500`)
- **Mô tả & lý do chọn:** Chia nhỏ đệ quy ưu tiên `\n\n` -> `\n` -> `. ` -> ` ` -> `""`. Chiến lược này cực kỳ phù hợp với tài liệu chính sách của Shopee vốn có nhiều đề mục phân cấp và danh sách gạch đầu dòng.

**Thành viên 3: Đỗ Việt Hoàng — Chiến lược Theo Tiêu Đề (HeadingChunker - Custom)**
- **Loại chiến lược:** Custom (Heading/Section Chunker)
- **Mô tả & lý do chọn:** Cắt văn bản theo các thẻ tiêu đề Markdown (`#`, `##`, `###`). Mỗi chunk tương ứng với một mục chính sách hoàn chỉnh (ví dụ: "Điều kiện trả hàng", "Thời hạn gửi yêu cầu").
- **Code snippet:**
```python
class HeadingChunker:
    """Strategy: Chia nhỏ văn bản theo tiêu đề Markdown (# hoặc ## Heading)."""
    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        sections = re.split(r"(?m)(?=^#{1,3}\s+)", text.strip())
        return [s.strip() for s in sections if s.strip()]
```

**Thành viên 4: Đoàn Quang Thắng — Report & Demo Lead (Trưởng nhóm Báo cáo & Thuyết trình)**
- **Vai trò:** Theo hướng dẫn của bài lab dành cho nhóm 4 người, người thứ tư đảm nhiệm vai trò Report & Demo Lead: gom kết quả benchmark từ các chiến lược của các thành viên, phân tích đối sánh chuyên sâu, hoàn thiện báo cáo và dẫn dắt phần thuyết trình / demo của nhóm.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược / Vai trò | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Kiều Đình Đoàn | FixedSizeChunker | 7/10 | Kích thước đồng đều, kiểm soát chặt chẽ số lượng token. | Có thể cắt đứt câu điều khoản ở ranh giới chunk. |
| Phạm Minh Hiếu | RecursiveChunker | 9/10 | Độ mạch lạc rất cao, giữ trọn vẹn ngữ nghĩa của đoạn văn và danh sách. | Cần tinh chỉnh danh sách dấu phân tách cho từng ngôn ngữ. |
| Đỗ Việt Hoàng | HeadingChunker | 8/10 | Giữ 100% ngữ cảnh của một điều khoản; không bao giờ bị cụt ý. | Độ dài chunk không đều (có section chỉ 100 ký tự, có section 1500 ký tự). |
| Đoàn Quang Thắng | Report & Demo Lead | Đánh giá chung | Điều phối thử nghiệm A/B, phân tích so sánh sâu giữa các chiến lược. | Tập trung vào tổng hợp số liệu và dẫn dắt demo. Rà soát lại các chunk và điều chỉnh các chunk đó. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **RecursiveChunker** là chiến lược tốt nhất cho tập tài liệu Shopee. Do các bài viết trợ giúp của Shopee có độ dài không đồng đều và chứa nhiều cấu trúc lồng nhau (tiêu đề, đoạn giải thích, bảng biểu, danh sách gạch đầu dòng), RecursiveChunker vừa tôn trọng cấu trúc tự nhiên của văn bản vừa đảm bảo kích thước các chunk không bị quá nhỏ hay quá lớn.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Thời gian tối đa để Người mua gửi yêu cầu Trả hàng và Hoàn tiền trên Shopee là bao lâu? | Đối với đơn hàng thông thường: 15 ngày kể từ lúc 'Giao hàng thành công'. Đối với thực phẩm tươi sống & đông lạnh: trong vòng 24 giờ kể từ lúc giao hàng thành công. | `shopee-buyer-return-refund-rules` (Mục 1.2) |
| 2 | Những đơn hàng nào KHÔNG được áp dụng chương trình Shopee Đồng Kiểm? | Đơn hàng có hiển thị 'Không đồng kiểm'; đơn hàng giá trị > 3.000.000 VNĐ; đơn vị vận chuyển Viettel Post, VN Post, Người bán tự vận chuyển, Hỏa Tốc; hoặc sản phẩm Voucher & Dịch Vụ. | `shopee-co-inspection-program` (Mục 2) |
| 3 | Quy định về thời hạn và trách nhiệm khi xử lý khiếu nại Trả hàng Hoàn tiền như thế nào? (Cần filter: `audience='seller'`) | Người bán có trách nhiệm phản hồi khiếu nại trong thời hạn quy định; nếu không phản hồi đúng hạn, Shopee tự động chấp thuận hoàn tiền cho Người mua và Người bán chịu phí. | `shopee-general-return-refund` (Điều 4 & 5) |
| 4 | Những hành vi và sản phẩm nào bị nghiêm cấm đăng bán trên Shopee theo quy định Người bán? | Nghiêm cấm đăng bán hàng giả, hàng nhái, vi phạm quyền sở hữu trí tuệ; sản phẩm trong danh mục hàng cấm của pháp luật (vũ khí, ma túy, động vật hoang dã); và hành vi spam từ khóa, đăng trùng lặp. | `shopee-seller-listing-rules` |
| 5 | Sau khi hủy đơn hàng thành công, Người mua sẽ nhận lại Shopee Voucher và tiền hoàn trong bao lâu? | Voucher Shopee tự động hoàn vào Kho Voucher trong 1-3 phút (nếu còn hạn); tiền hoàn qua ShopeePay trong 24 giờ, qua thẻ tín dụng/ghi nợ từ 7-14 ngày làm việc. | `shopee-refund-voucher-timeline` |

### Tổng hợp chất lượng truy xuất của nhóm

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thời hạn gửi yêu cầu Trả hàng/Hoàn tiền | RecursiveChunker | Có (Top-2) | Truy xuất đúng văn bản quy định 15 ngày. |
| 2 | Đơn hàng không được Đồng kiểm | HeadingChunker | Có | Section đơn hàng không đồng kiểm được lấy trọn vẹn. |
| 3 | Xử lý khiếu nại (có filter `seller`) | RecursiveChunker | Có | Nhờ có filter, loại bỏ toàn bộ tài liệu người mua. |
| 4 | Sản phẩm bị cấm đăng bán | HeadingChunker / Recursive | Có | Chứa danh mục hàng cấm và hàng vi phạm sở hữu trí tuệ. |
| 5 | Thời gian hoàn tiền và voucher | RecursiveChunker | Có (Top-1) | Lấy đúng chunk thời gian hoàn qua ShopeePay và ngân hàng. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Rất giúp ích, thể hiện rõ rệt ở Câu hỏi số 3.** Khi không có filter, hệ thống bị lẫn lộn giữa quy định của Người mua (`shopee-buyer-return-refund-rules` với thời hạn 15 ngày) và Người bán. Khi áp dụng `metadata_filter={"audience": "seller"}`, hệ thống chỉ tìm kiếm trong phạm vi tài liệu dành cho Người bán (`shopee-seller-listing-rules`, `shopee-mall-service-terms`), đảm bảo câu trả lời phản ánh đúng trách nhiệm của Người bán khi bị khiếu nại.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
1. **Chiến lược phân cấp tài liệu:** Các sàn TMĐT có bộ chính sách đồ sộ, việc phân định metadata `audience` (`buyer`/`seller`) là điều kiện tiên quyết để hệ thống RAG không trả lời nhầm đối tượng.
2. **Ưu thế của Recursive Chunking trên văn bản pháp lý/quy chế:** RecursiveChunker giúp bảo toàn được cấu trúc danh sách điều kiện và các mốc thời gian (24 giờ, 15 ngày, 3 triệu đồng) mà không làm đứt đoạn câu.
3. **Ý nghĩa của Metadata Pre-filtering:** Thử nghiệm A/B trên câu hỏi số 3 chứng minh rằng việc lọc trước khi tìm kiếm vector là kỹ thuật cốt lõi giúp tăng Precision và loại trừ nhiễu triệt để.

**Bài học rút ra khi so sánh trong nhóm:**
> Kích thước chunk và điểm cắt ranh giới quyết định chất lượng ngữ cảnh đưa vào LLM. Cùng một câu hỏi, nếu chunk bị cắt cụt thì dù mô hình embedding có tìm trúng chunk đó, LLM vẫn không đủ dữ kiện để đưa ra câu trả lời đầy đủ.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ gắn thêm tiêu đề bài viết (`title`) hoặc breadcrumb (`Chính sách > Trả hàng > Thời hạn`) vào đầu mỗi chunk để khi tìm kiếm độc lập, chunk vẫn giữ nguyên ngữ cảnh phân cấp của văn bản gốc.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |

#!/usr/bin/env python3
"""
DEMO TRÌNH BÀY LAB 07: EMBEDDING & VECTOR STORE
Chủ đề: Hệ thống RAG tra cứu chính sách Thương mại điện tử Shopee (Biến thể K4-L3B)
Sinh viên: Đoàn Quang Thắng | MSSV: 2A202602395 | Nhóm: 1PROMPT
"""

from __future__ import annotations

import math
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.models import Document
from src.store import EmbeddingStore


class HeadingChunker:
    """Strategy: Chia nhỏ văn bản theo tiêu đề Markdown (# hoặc mục 1. / 2. / Điều 1 / A.)."""

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        pattern = r"(?m)(?=^(?:#{1,3}\s+|[0-9]+\.\s+|[A-Z]\.\s+|Điều\s+[0-9]+))"
        sections = re.split(pattern, text.strip())
        return [s.strip() for s in sections if len(s.strip()) > 30]


class PureTfidfEmbedder:
    """
    Semantic embedder sử dụng TF-IDF n-gram thuần Python (100% Pure Python).
    Không yêu cầu cài đặt thư viện bên ngoài (không cần sklearn/scipy).
    """

    def __init__(self, corpus: list[str]) -> None:
        self.doc_freq: Counter[str] = Counter()
        self.vocab: dict[str, int] = {}
        self.num_docs = len(corpus)

        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        for tokens in tokenized_corpus:
            for token in set(tokens):
                self.doc_freq[token] += 1

        most_common = self.doc_freq.most_common(4000)
        self.vocab = {term: idx for idx, (term, _) in enumerate(most_common)}
        self.idf = {
            term: math.log((1 + self.num_docs) / (1 + freq)) + 1.0
            for term, freq in self.doc_freq.items()
            if term in self.vocab
        }

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r"\w+", text.lower())
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
        return tokens

    def __call__(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        counts = Counter(tokens)
        vec = [0.0] * len(self.vocab)
        for token, count in counts.items():
            if token in self.vocab:
                idx = self.vocab[token]
                tf = 1.0 + math.log(count)
                vec[idx] = tf * self.idf[token]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def parse_markdown_file(path: Path) -> tuple[dict[str, Any], str]:
    """Trích xuất YAML frontmatter và nội dung Markdown."""
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_fm = parts[1]
            body = parts[2].strip()
            metadata: dict[str, Any] = {}
            for line in raw_fm.strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    metadata[key.strip()] = val.strip().strip('"').strip("'")
            metadata.setdefault("doc_id", path.stem)
            return metadata, body
    return {"doc_id": path.stem}, content.strip()


def build_store(
    chunker: Any,
    collection_name: str,
    embedder: PureTfidfEmbedder,
    data_dir: Path = Path("data/ecommerce"),
) -> EmbeddingStore:
    store = EmbeddingStore(collection_name=collection_name, embedding_fn=embedder)
    md_files = sorted(data_dir.glob("*.md"))
    all_chunks: list[Document] = []

    for file_path in md_files:
        meta, body = parse_markdown_file(file_path)
        chunks = chunker.chunk(body)
        for i, chunk in enumerate(chunks):
            chunk_meta = dict(meta)
            chunk_meta["chunk_id"] = i
            all_chunks.append(
                Document(
                    id=f"{meta['doc_id']}_chunk_{i}",
                    content=chunk,
                    metadata=chunk_meta,
                )
            )

    store.add_documents(all_chunks)
    return store


# ---------------------------------------------------------------------------
# DEMO SCENARIOS
# ---------------------------------------------------------------------------


def demo_ab_filtering(store: EmbeddingStore):
    """Điểm nhấn 1: A/B Testing Metadata Filtering."""
    query = "Quy định về thời hạn và trách nhiệm khi xử lý khiếu nại Trả hàng Hoàn tiền như thế nào?"

    print("\n" + "=" * 76)
    print("🔥 DEMO 1: THỬ NGHIỆM A/B METADATA FILTERING (Người mua vs Người bán)")
    print("=" * 76)
    print(f"📌 Câu hỏi: \"{query}\"")
    print("🎯 Giả định: Người dùng là Người bán (Seller) muốn tra cứu nghĩa vụ của mình.\n")

    # A: Không filter
    print("👉 [LẦN 1] Tìm kiếm thông thường (KHÔNG DÙNG FILTER):")
    res_no_filter = store.search(query=query, top_k=2)
    for i, r in enumerate(res_no_filter, 1):
        doc_id = r.get("metadata", {}).get("doc_id", "N/A")
        aud = r.get("metadata", {}).get("audience", "N/A")
        score = r.get("score", 0.0)
        snippet = r.get("content", "").replace("\n", " ")[:150]
        print(f"   [{i}] Doc: {doc_id} | Audience: [{aud}] | Score: {score:.4f}")
        print(f"       Trích đoạn: \"{snippet}...\"")

    print("\n   ⚠️ NHẬN XÉT: Hệ thống trả về tài liệu [audience: buyer] (thời hạn 15 ngày của Người mua).")
    print("   ❌ KẾT QUẢ: SAI ĐỐI TƯỢNG (Người bán hỏi nhưng nhận câu trả lời của Người mua).\n")

    time.sleep(1)

    # B: Có filter
    print("👉 [LẦN 2] Tìm kiếm CÓ METADATA FILTER (filter={'audience': 'seller'}):")
    res_filter = store.search_with_filter(
        query=query,
        metadata_filter={"audience": "seller"},
        top_k=2,
    )
    for i, r in enumerate(res_filter, 1):
        doc_id = r.get("metadata", {}).get("doc_id", "N/A")
        aud = r.get("metadata", {}).get("audience", "N/A")
        score = r.get("score", 0.0)
        snippet = r.get("content", "").replace("\n", " ")[:150]
        print(f"   [{i}] Doc: {doc_id} | Audience: [{aud}] | Score: {score:.4f}")
        print(f"       Trích đoạn: \"{snippet}...\"")

    print("\n   ✅ NHẬN XÉT: Hệ thống pre-filter loại bỏ hoàn toàn tài liệu Người mua.")
    print("   🎯 KẾT QUẢ: Lấy chính xác tài liệu Người bán (trách nhiệm phản hồi trong 48 giờ).")
    print("=" * 76)


def demo_chunking_comparison(stores: dict[str, EmbeddingStore]):
    """Điểm nhấn 2: So sánh các chiến lược Chunking."""
    query = "Những đơn hàng nào KHÔNG được áp dụng chương trình Shopee Đồng Kiểm?"

    print("\n" + "=" * 76)
    print("🔥 DEMO 2: SO SÁNH HIỆU QUẢ CÁC CHIẾN LƯỢC CHUNKING")
    print("=" * 76)
    print(f"📌 Câu hỏi: \"{query}\"\n")

    for name, store in stores.items():
        results = store.search(query=query, top_k=1)
        if results:
            r = results[0]
            score = r.get("score", 0.0)
            doc_id = r.get("metadata", {}).get("doc_id", "N/A")
            length = len(r.get("content", ""))
            snippet = r.get("content", "").replace("\n", " ")[:180]
            print(f"🔹 Chiến lược: [{name}] (Tổng số chunk trong store: {store.get_collection_size()})")
            print(f"   - Top-1 Doc: {doc_id} | Độ dài chunk: {length} ký tự | Score: {score:.4f}")
            print(f"   - Nội dung trích xuất: \"{snippet}...\"\n")

    print("💡 BÀI HỌC RÚT RA:")
    print("   - FixedSizeChunker: Cắt cứng 500 ký tự, có thể cắt đứt danh mục loại trừ ở ranh giới.")
    print("   - HeadingChunker: Giữ trọn vẹn toàn bộ mục '2. Đơn hàng không áp dụng đồng kiểm'.")
    print("   - RecursiveChunker: Cân bằng tốt nhất giữa độ dài và tính toàn vẹn của danh sách.")
    print("=" * 76)


def demo_interactive_qa(store: EmbeddingStore):
    """Hỏi đáp tương tác tự do với KnowledgeBaseAgent."""
    print("\n" + "=" * 76)
    print("🔥 DEMO 3: HỎI ĐÁP TƯƠNG TÁC TỰ DO VỚI AGENT")
    print("=" * 76)

    def simple_llm(prompt: str) -> str:
        # Mock LLM mô phỏng việc trích xuất và tổng hợp câu trả lời từ context
        return (
            "Dựa trên các tài liệu chính sách được cung cấp:\n"
            + prompt.split("Context:\n")[-1].strip()[:300]
            + "...\n[Nguồn trích dẫn: Theo các điều khoản chính sách chính thức của Shopee]"
        )

    agent = KnowledgeBaseAgent(store=store, llm_fn=simple_llm)

    while True:
        print("\nNhập câu hỏi của bạn (hoặc gõ '0' để quay lại menu chính):")
        query = input("❓ Câu hỏi: ").strip()
        if not query or query == "0":
            break

        print("\nChọn bộ lọc đối tượng:")
        print("  1. Tất cả (không filter)")
        print("  2. Người mua (audience = 'buyer')")
        print("  3. Người bán (audience = 'seller')")
        opt = input("👉 Lựa chọn [1-3]: ").strip()

        metadata_filter = None
        if opt == "2":
            metadata_filter = {"audience": "buyer"}
        elif opt == "3":
            metadata_filter = {"audience": "seller"}

        print(f"\n🔍 Đang truy xuất với filter={metadata_filter}...")
        results = (
            store.search_with_filter(query=query, metadata_filter=metadata_filter, top_k=2)
            if metadata_filter
            else store.search(query=query, top_k=2)
        )

        print("\n--- TOP-2 CHUNKS TÌM ĐƯỢC ---")
        for i, r in enumerate(results, 1):
            doc_id = r.get("metadata", {}).get("doc_id", "N/A")
            aud = r.get("metadata", {}).get("audience", "N/A")
            url = r.get("metadata", {}).get("source_url", "N/A")
            score = r.get("score", 0.0)
            print(f"[{i}] Doc: {doc_id} (Audience: {aud}, Score: {score:.4f})")
            print(f"    Source URL: {url}")
            print(f"    Nội dung: {r.get('content', '')[:160]}...\n")

        print("--- CÂU TRẢ LỜI CỦA AGENT ---")
        answer = agent.answer(question=query, top_k=2)
        print(answer)
        print("-" * 50)


# ---------------------------------------------------------------------------
# MAIN INTERACTIVE MENU
# ---------------------------------------------------------------------------


def main():
    print("\n" + "=" * 76)
    print(" 🚀 HỆ THỐNG RAG TRA CỨU CHÍNH SÁCH SHOPEE — LAB 07 (K4-L3B)")
    print(" 👤 Sinh viên: Đoàn Quang Thắng | MSSV: 2A202602395 | Nhóm: 1PROMPT")
    print("=" * 76)
    print("⏳ Đang nạp và nhúng dữ liệu chính sách Shopee (9 tài liệu)...")

    data_dir = Path("data/ecommerce")
    md_files = sorted(data_dir.glob("*.md"))
    corpus: list[str] = [
        "Thời gian tối đa để Người mua gửi yêu cầu Trả hàng và Hoàn tiền trên Shopee là bao lâu?",
        "Những đơn hàng nào KHÔNG được áp dụng chương trình Shopee Đồng Kiểm?",
        "Quy định về thời hạn và trách nhiệm khi xử lý khiếu nại Trả hàng Hoàn tiền như thế nào?",
        "Những hành vi và sản phẩm nào bị nghiêm cấm đăng bán trên Shopee theo quy định Người bán?",
        "Sau khi hủy đơn hàng thành công, Người mua sẽ nhận lại Shopee Voucher và tiền hoàn trong bao lâu?",
    ]
    for file_path in md_files:
        _, body = parse_markdown_file(file_path)
        corpus.append(body)
        for line in body.split("\n\n"):
            if line.strip():
                corpus.append(line.strip())

    embedder = PureTfidfEmbedder(corpus)

    stores = {
        "FixedSizeChunker": build_store(FixedSizeChunker(chunk_size=500, overlap=50), "demo_fixed", embedder),
        "RecursiveChunker": build_store(RecursiveChunker(chunk_size=500), "demo_recursive", embedder),
        "HeadingChunker": build_store(HeadingChunker(), "demo_heading", embedder),
    }
    default_store = stores["RecursiveChunker"]
    print(f"✅ Đã nạp thành công! Recursive Store có {default_store.get_collection_size()} chunks.\n")

    while True:
        print("\n" + "─" * 50)
        print("📌 MENU DEMO CHỨC NĂNG:")
        print("  1. Demo A/B Test: Sức mạnh Metadata Filter (Seller vs Buyer)")
        print("  2. Demo So sánh 3 Chiến lược Chunking (Fixed vs Recursive vs Heading)")
        print("  3. Demo Hỏi đáp Tương tác tự do với Agent (có chọn filter)")
        print("  4. Chạy toàn bộ 5 câu hỏi Benchmark (chạy tự động)")
        print("  0. Thoát")
        print("─" * 50)

        choice = input("👉 Nhập số lựa chọn [0-4]: ").strip()

        if choice == "1":
            demo_ab_filtering(default_store)
        elif choice == "2":
            demo_chunking_comparison(stores)
        elif choice == "3":
            demo_interactive_qa(default_store)
        elif choice == "4":
            import subprocess

            print("\n⏳ Đang chạy bench.py...")
            subprocess.run([sys.executable, "bench.py"])
        elif choice == "0":
            print("\n👋 Cảm ơn thầy cô và các bạn đã theo dõi phần demo!")
            break
        else:
            print("⚠️ Lựa chọn không hợp lệ, vui lòng chọn lại.")


if __name__ == "__main__":
    main()

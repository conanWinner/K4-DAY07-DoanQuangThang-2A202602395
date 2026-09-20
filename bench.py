from __future__ import annotations

import math
import re
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
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    metadata[key] = val
            metadata.setdefault("doc_id", path.stem)
            return metadata, body
    return {"doc_id": path.stem}, content.strip()


BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Thời gian tối đa để Người mua gửi yêu cầu Trả hàng và Hoàn tiền trên Shopee là bao lâu?",
        "gold_answer": "Đối với đơn hàng thông thường: 15 ngày kể từ lúc 'Giao hàng thành công'. Đối với thực phẩm tươi sống & đông lạnh: trong vòng 24 giờ kể từ lúc giao hàng thành công.",
        "filter": None,
    },
    {
        "id": 2,
        "query": "Những đơn hàng nào KHÔNG được áp dụng chương trình Shopee Đồng Kiểm?",
        "gold_answer": "Đơn hàng có hiển thị 'Không đồng kiểm'; đơn hàng giá trị > 3.000.000 VNĐ; đơn vị vận chuyển Viettel Post, VN Post, Người bán tự vận chuyển, Hỏa Tốc; hoặc sản phẩm Voucher & Dịch Vụ.",
        "filter": None,
    },
    {
        "id": 3,
        "query": "Quy định về thời hạn và trách nhiệm khi xử lý khiếu nại Trả hàng Hoàn tiền như thế nào?",
        "gold_answer": "Người bán có trách nhiệm phản hồi khiếu nại trong thời hạn quy định; nếu không phản hồi đúng hạn, Shopee tự động chấp thuận hoàn tiền cho Người mua và Người bán chịu phí.",
        "filter": {"audience": "seller"},
    },
    {
        "id": 4,
        "query": "Những hành vi và sản phẩm nào bị nghiêm cấm đăng bán trên Shopee theo quy định Người bán?",
        "gold_answer": "Nghiêm cấm đăng bán hàng giả, hàng nhái, vi phạm quyền sở hữu trí tuệ; sản phẩm trong danh mục hàng cấm của pháp luật (vũ khí, ma túy, động vật hoang dã); và hành vi spam từ khóa, đăng trùng lặp.",
        "filter": None,
    },
    {
        "id": 5,
        "query": "Sau khi hủy đơn hàng thành công, Người mua sẽ nhận lại Shopee Voucher và tiền hoàn trong bao lâu?",
        "gold_answer": "Voucher Shopee tự động hoàn vào Kho Voucher trong 1-3 phút (nếu còn hạn); tiền hoàn qua ShopeePay trong 24 giờ, qua thẻ tín dụng/ghi nợ từ 7-14 ngày làm việc.",
        "filter": None,
    },
]


def run_benchmark(
    strategy_name: str,
    chunker: Any,
    embedder: PureTfidfEmbedder,
    data_dir: Path = Path("data/ecommerce"),
):
    print(f"\n{'='*70}")
    print(f"BẮT ĐẦU BENCHMARK: Chiến lược [{strategy_name}]")
    print(f"{'='*70}")

    store = EmbeddingStore(
        collection_name=f"benchmark_{strategy_name}",
        embedding_fn=embedder,
    )
    md_files = sorted(data_dir.glob("*.md"))
    all_chunks: list[Document] = []

    for file_path in md_files:
        meta, body = parse_markdown_file(file_path)
        chunks = chunker.chunk(body)
        for i, chunk in enumerate(chunks):
            doc_id = f"{file_path.stem}#{i}"
            doc = Document(
                id=doc_id,
                content=chunk,
                metadata={**meta, "doc_id": file_path.stem, "chunk_id": doc_id},
            )
            all_chunks.append(doc)

    store.add_documents(all_chunks)
    print(f"Đã nạp {len(md_files)} tài liệu, tổng cộng {len(all_chunks)} chunks vào store.")

    def simple_llm(prompt: str) -> str:
        return "[RAG Trả lời dựa trên ngữ cảnh đã truy xuất]"

    agent = KnowledgeBaseAgent(store=store, llm_fn=simple_llm)

    for q in BENCHMARK_QUERIES:
        qid = q["id"]
        query = q["query"]
        gold = q["gold_answer"]
        meta_filter = q["filter"]

        print(f"\n--- Câu hỏi {qid}: {query} ---")
        print(f"Câu trả lời chuẩn (Gold): {gold}")
        if meta_filter:
            print(f"Bộ lọc metadata: {meta_filter}")
            results = store.search_with_filter(query, top_k=3, metadata_filter=meta_filter)
        else:
            results = store.search(query, top_k=3)

        for rank, r in enumerate(results, 1):
            doc_id = r["metadata"].get("doc_id")
            score = r["score"]
            preview = r["content"].replace("\n", " ")[:140]
            print(f"  Top-{rank} [{doc_id}] (Score: {score:.4f}): {preview}...")

    # A/B Testing cho Câu 3 (có filter vs không filter)
    print("\n--- THỬ NGHIỆM A/B: Câu 3 (Có Filter vs Không Filter) ---")
    q3 = BENCHMARK_QUERIES[2]
    res_no_filter = store.search(q3["query"], top_k=3)
    res_with_filter = store.search_with_filter(
        q3["query"], top_k=3, metadata_filter=q3["filter"]
    )

    print("Kết quả KHÔNG có filter (có nguy cơ lẫn tài liệu người mua):")
    for rank, r in enumerate(res_no_filter, 1):
        print(
            f"  Top-{rank} [{r['metadata'].get('doc_id')}] (Audience: {r['metadata'].get('audience')}): {r['content'].replace(chr(10), ' ')[:100]}..."
        )

    print("\nKết quả CÓ filter audience='seller' (chính xác đối tượng người bán):")
    for rank, r in enumerate(res_with_filter, 1):
        print(
            f"  Top-{rank} [{r['metadata'].get('doc_id')}] (Audience: {r['metadata'].get('audience')}): {r['content'].replace(chr(10), ' ')[:100]}..."
        )


def main():
    data_dir = Path("data/ecommerce")
    md_files = sorted(data_dir.glob("*.md"))

    corpus: list[str] = [q["query"] for q in BENCHMARK_QUERIES]
    for file_path in md_files:
        _, body = parse_markdown_file(file_path)
        corpus.append(body)
        for line in body.split("\n\n"):
            if line.strip():
                corpus.append(line.strip())

    embedder = PureTfidfEmbedder(corpus)

    strategies = {
        "FixedSize": FixedSizeChunker(chunk_size=500, overlap=50),
        "Recursive": RecursiveChunker(chunk_size=500),
        "Heading": HeadingChunker(),
    }

    for name, chunker in strategies.items():
        run_benchmark(name, chunker, embedder, data_dir)


if __name__ == "__main__":
    main()

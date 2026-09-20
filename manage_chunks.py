#!/usr/bin/env python3
"""
CÔNG CỤ QUẢN LÝ VÀ XUẤT CHUNKS THEO NHIỀU CHIẾN LƯỢC ĐỒNG THỜI
Hỗ trợ 3 chiến lược:
1. recursive:  RecursiveChunker (chunk_size=500)
2. fixed_size: FixedSizeChunker (chunk_size=500, overlap=50)
3. heading:    HeadingChunker (cắt theo tiêu đề Markdown #, ##, ###)
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from bench import parse_markdown_file
from src.chunking import FixedSizeChunker, RecursiveChunker
from src.models import Document


CHUNKS_DIR = Path("data/chunks")
ECOMMERCE_DIR = Path("data/ecommerce")


class HeadingChunker:
    """Strategy: Chia nhỏ văn bản theo tiêu đề Markdown (# hoặc mục 1. / 2. / Điều 1 / A.)."""

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        pattern = r"(?m)(?=^(?:#{1,3}\s+|[0-9]+\.\s+|[A-Z]\.\s+|Điều\s+[0-9]+))"
        sections = re.split(pattern, text.strip())
        return [s.strip() for s in sections if len(s.strip()) > 30]


STRATEGIES: dict[str, Any] = {
    "recursive": RecursiveChunker(chunk_size=500),
    "fixed_size": FixedSizeChunker(chunk_size=500, overlap=50),
    "heading": HeadingChunker(),
}


def export_single_strategy(strat_name: str, chunker: Any, md_files: list[Path]) -> int:
    """Xuất chunks cho một chiến lược cụ thể vào data/chunks/<strat_name>/."""
    strat_dir = CHUNKS_DIR / strat_name
    if strat_dir.exists():
        shutil.rmtree(strat_dir)
    strat_dir.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    all_chunks_data: list[dict[str, Any]] = []

    print(f"📦 Đang xuất chiến lược [{strat_name}]...")

    for file_path in md_files:
        meta, body = parse_markdown_file(file_path)
        doc_id = meta.get("doc_id", file_path.stem)
        doc_chunk_dir = strat_dir / doc_id
        doc_chunk_dir.mkdir(parents=True, exist_ok=True)

        chunks = chunker.chunk(body)
        total_chunks += len(chunks)

        for idx, chunk_text in enumerate(chunks, 1):
            chunk_file = doc_chunk_dir / f"chunk_{idx:03d}.md"

            # YAML frontmatter
            frontmatter_lines = ["---"]
            for k, v in meta.items():
                frontmatter_lines.append(f"{k}: \"{v}\"")
            frontmatter_lines.append(f"strategy: \"{strat_name}\"")
            frontmatter_lines.append(f"chunk_index: {idx}")
            frontmatter_lines.append(f"char_count: {len(chunk_text)}")
            frontmatter_lines.append("---\n")

            content_to_write = "\n".join(frontmatter_lines) + chunk_text.strip() + "\n"
            chunk_file.write_text(content_to_write, encoding="utf-8")

            all_chunks_data.append({
                "id": f"{strat_name}_{doc_id}_chunk_{idx}",
                "doc_id": doc_id,
                "strategy": strat_name,
                "chunk_index": idx,
                "metadata": meta,
                "content": chunk_text.strip(),
                "file_path": str(chunk_file),
            })

    # Lưu thêm 1 file JSON tổng hợp cho từng chiến lược
    json_path = strat_dir / "all_chunks.json"
    json_path.write_text(json.dumps(all_chunks_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"   ↳ Hoàn tất [{strat_name}]: {total_chunks} chunks -> {strat_dir}")
    return total_chunks


def export_all_strategies() -> None:
    """Xuất đồng thời cả 3 chiến lược vào data/chunks/."""
    md_files = sorted(ECOMMERCE_DIR.glob("*.md"))
    print(f"🚀 BẮT ĐẦU XUẤT ĐỒNG THỜI 3 CHIẾN LƯỢC CHO {len(md_files)} TÀI LIỆU:\n")

    summary = {}
    for strat_name, chunker in STRATEGIES.items():
        count = export_single_strategy(strat_name, chunker, md_files)
        summary[strat_name] = count

    print("\n" + "=" * 60)
    print("🎉 XUẤT HOÀN TẤT TOÀN BỘ CÁC CHIẾN LƯỢC:")
    for s_name, s_count in summary.items():
        print(f"   • {s_name:<12}: {s_count:>4} chunks  --> data/chunks/{s_name}/")
    print("=" * 60)
    print("👉 Bây giờ bạn có thể mở từng thư mục con để so sánh bằng mắt và sửa tay tùy ý!\n")


def load_curated_chunks(strategy: str = "recursive") -> list[Document]:
    """
    Đọc lại toàn bộ các chunk từ thư mục chiến lược tương ứng trong data/chunks/<strategy>/
    (bao gồm cả các đoạn bạn đã sửa tay) để nạp vào EmbeddingStore.
    """
    strat_dir = CHUNKS_DIR / strategy
    if not strat_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục {strat_dir}. Hãy chạy export trước!")

    documents: list[Document] = []
    chunk_files = sorted(strat_dir.rglob("chunk_*.md"))

    for chunk_file in chunk_files:
        meta, body = parse_markdown_file(chunk_file)
        doc_id = meta.get("doc_id", chunk_file.parent.name)
        chunk_idx = meta.get("chunk_index", chunk_file.stem)
        chunk_id = f"{strategy}_{doc_id}_{chunk_idx}"

        documents.append(
            Document(
                id=chunk_id,
                content=body,
                metadata=meta,
            )
        )

    return documents


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "load":
        target_strat = sys.argv[2] if len(sys.argv) > 2 else "recursive"
        docs = load_curated_chunks(strategy=target_strat)
        print(f"✅ Đã nạp thành công {len(docs)} chunks từ chiến lược '{target_strat}'!")
    else:
        export_all_strategies()

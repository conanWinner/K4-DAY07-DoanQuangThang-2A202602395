from __future__ import annotations

from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy thông tin phù hợp trong cơ sở tri thức."

        context_blocks: list[str] = []
        for i, r in enumerate(results, 1):
            source = r.get("metadata", {}).get("source_url") or r.get("id", f"doc_{i}")
            context_blocks.append(f"[{i}] (Nguồn: {source}):\n{r['content']}")

        context_str = "\n\n".join(context_blocks)
        prompt = (
            f"Hãy trả lời câu hỏi dựa trên ngữ cảnh được cung cấp sau đây.\n\n"
            f"Ngữ cảnh:\n{context_str}\n\n"
            f"Câu hỏi: {question}\n\n"
            f"Câu trả lời:"
        )
        return self.llm_fn(prompt)

from typing import TypedDict

from rag.retriever import RetrievedChunk


class ContextResult(TypedDict):
    context: str
    citations: list[str]


def build(chunks: list[RetrievedChunk]) -> ContextResult:
    blocks: list[str] = []
    seen_citations: list[str] = []

    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        article = meta.get("article_number", "")
        regulation = meta.get("regulation", "")
        citation = f"[{article}, {regulation}]" if article and regulation else ""

        block = f"[{i}] {chunk['text']}"
        if citation:
            block += f" {citation}"
        blocks.append(block)

        if citation and citation not in seen_citations:
            seen_citations.append(citation)

    return ContextResult(
        context="\n\n".join(blocks),
        citations=seen_citations,
    )

from typing import Any, TypedDict

import tiktoken

from ingestion.sources.gdpr import Document

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class Chunk(TypedDict):
    id: str
    text: str
    metadata: dict[str, Any]


def _count_tokens(text: str, enc: tiktoken.Encoding) -> int:
    return len(enc.encode(text))


def _split_text(text: str, chunk_size: int, overlap: int, enc: tiktoken.Encoding) -> list[str]:
    """Recursively split text until every piece fits within chunk_size tokens."""
    if _count_tokens(text, enc) <= chunk_size:
        return [text]

    for sep in _SEPARATORS:
        if sep and sep in text:
            parts = text.split(sep)
            break
    else:
        # No separator found — hard split by words
        words = text.split()
        parts = []
        current: list[str] = []
        current_tokens = 0
        for word in words:
            wt = _count_tokens(word, enc)
            if current_tokens + wt > chunk_size and current:
                parts.append(" ".join(current))
                current = current[-overlap:] if overlap else []
                current_tokens = _count_tokens(" ".join(current), enc)
            current.append(word)
            current_tokens += wt
        if current:
            parts.append(" ".join(current))
        return parts

    # Merge parts back respecting chunk_size with overlap
    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for part in parts:
        part_tokens = _count_tokens(part + sep, enc)
        if current_tokens + part_tokens > chunk_size and current_parts:
            chunks.append(sep.join(current_parts))
            # Keep overlap
            overlap_parts: list[str] = []
            overlap_tokens = 0
            for p in reversed(current_parts):
                pt = _count_tokens(p + sep, enc)
                if overlap_tokens + pt > overlap:
                    break
                overlap_parts.insert(0, p)
                overlap_tokens += pt
            current_parts = overlap_parts
            current_tokens = overlap_tokens
        current_parts.append(part)
        current_tokens += part_tokens

    if current_parts:
        chunks.append(sep.join(current_parts))

    # Recurse on any chunks still too large
    result: list[str] = []
    for c in chunks:
        if _count_tokens(c, enc) > chunk_size:
            result.extend(_split_text(c, chunk_size, overlap, enc))
        else:
            result.append(c)
    return result


def chunk(
    documents: list[Document],
    chunk_size: int = 512,
    overlap: int = 50,
) -> list[Chunk]:
    enc = tiktoken.get_encoding("cl100k_base")
    chunks: list[Chunk] = []

    for doc in documents:
        pieces = _split_text(doc["text"], chunk_size, overlap, enc)
        for idx, piece in enumerate(pieces):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                Chunk(
                    id=f"{doc['id']}-{idx}",
                    text=piece,
                    metadata={
                        "article_number": doc["article_number"],
                        "title": doc["title"],
                        "regulation": doc["regulation"],
                        "chapter": doc["chapter"],
                        "source_id": doc["id"],
                    },
                )
            )

    return chunks

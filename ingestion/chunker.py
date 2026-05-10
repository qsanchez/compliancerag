from typing import Any, TypedDict

import tiktoken

from ingestion.types import Document


class Chunk(TypedDict):
    id: str
    text: str
    metadata: dict[str, Any]


def _split_text(text: str, chunk_size: int, overlap: int, enc: tiktoken.Encoding) -> list[str]:
    """Token-based sliding window split — no recursion, guaranteed termination."""
    tokens = enc.encode(text)
    if len(tokens) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(enc.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start = end - overlap

    return chunks


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

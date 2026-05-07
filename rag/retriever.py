import json
from typing import Any, TypedDict

from config import get_settings
from ingestion import embedder, indexer


class RetrievedChunk(TypedDict):
    text: str
    metadata: dict[str, Any]
    score: float


def _retrieve_chroma(query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
    collection = indexer.get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    chunks: list[RetrievedChunk] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Chroma cosine distance: 0 = identical, 2 = opposite → convert to similarity
        chunks.append(RetrievedChunk(text=doc, metadata=meta, score=1.0 - (dist / 2.0)))
    return chunks


def _retrieve_pgvector(query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
    with indexer._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT document, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, top_k),
            )
            rows = cur.fetchall()

    return [
        RetrievedChunk(
            text=row[0],
            metadata=json.loads(row[1]) if isinstance(row[1], str) else row[1],
            score=float(row[2]),
        )
        for row in rows
    ]


def retrieve(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_embedding = embedder.embed([query])[0]
    settings = get_settings()
    if settings.vector_store == "pgvector":
        return _retrieve_pgvector(query_embedding, top_k)
    return _retrieve_chroma(query_embedding, top_k)

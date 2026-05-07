from typing import Any, TypedDict

from ingestion import embedder, indexer


class RetrievedChunk(TypedDict):
    text: str
    metadata: dict[str, Any]
    score: float


def retrieve(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_embedding = embedder.embed([query])[0]
    collection = indexer.get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        # Chroma cosine distance: 0 = identical, 2 = opposite. Convert to similarity score.
        score = 1.0 - (dist / 2.0)
        chunks.append(RetrievedChunk(text=doc, metadata=meta, score=score))

    return chunks

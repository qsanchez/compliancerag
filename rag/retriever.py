import json
from typing import Any, TypedDict

from langsmith import traceable

from vectorstore import client, embedder

# Reciprocal Rank Fusion constant — higher k reduces the impact of top-rank
# dominance; 60 is the standard value from the original RRF paper.
_RRF_K = 60


class RetrievedChunk(TypedDict):
    text: str
    metadata: dict[str, Any]
    score: float


@traceable(name="retrieve", run_type="retriever")
def retrieve(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_embedding = embedder.embed([query])[0]
    fetch_k = top_k * 3  # fetch more candidates from each leg before fusion

    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            # Semantic leg: cosine ANN via HNSW
            cur.execute(
                """
                SELECT id, document, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, fetch_k),
            )
            semantic_rows = cur.fetchall()

            # Keyword leg: pg_trgm word_similarity
            # word_similarity(needle, haystack) — matches query as a subsequence,
            # better than similarity() when the query is shorter than the document.
            cur.execute(
                """
                SELECT id, document, metadata,
                       word_similarity(%s, document) AS score
                FROM embeddings
                ORDER BY word_similarity(%s, document) DESC
                LIMIT %s
                """,
                (query, query, fetch_k),
            )
            keyword_rows = cur.fetchall()

    # Build id → row map for later lookup
    rows_by_id: dict[str, tuple] = {}
    for row in semantic_rows + keyword_rows:
        rows_by_id[row[0]] = row

    # RRF fusion: score = Σ 1/(k + rank) across both ranked lists
    rrf_scores: dict[str, float] = {}
    for rank, row in enumerate(semantic_rows, start=1):
        doc_id = row[0]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (_RRF_K + rank)
    for rank, row in enumerate(keyword_rows, start=1):
        doc_id = row[0]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (_RRF_K + rank)

    top_ids = sorted(rrf_scores, key=rrf_scores.__getitem__, reverse=True)[:top_k]

    return [
        RetrievedChunk(
            text=rows_by_id[doc_id][1],
            metadata=(
                json.loads(rows_by_id[doc_id][2])
                if isinstance(rows_by_id[doc_id][2], str)
                else rows_by_id[doc_id][2]
            ),
            score=rrf_scores[doc_id],
        )
        for doc_id in top_ids
    ]

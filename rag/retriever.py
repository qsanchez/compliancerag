import json
from typing import Any, TypedDict

from vectorstore import client, embedder

# Reciprocal Rank Fusion constant — higher k reduces the impact of top-rank
# dominance; 60 is the standard value from the original RRF paper.
_RRF_K = 60

_KNOWN_REGULATIONS: frozenset[str] = frozenset({"gdpr", "nis2", "dora"})


class RetrievedChunk(TypedDict):
    text: str
    metadata: dict[str, Any]
    score: float


def _detect_regulations(query: str) -> list[str]:
    """Return uppercase regulation names explicitly mentioned in the query."""
    q = query.lower()
    return sorted(reg.upper() for reg in _KNOWN_REGULATIONS if reg in q)


def _fetch_legs(
    cur: Any,
    query: str,
    query_embedding: list[float],
    fetch_k: int,
    regulation: str | None,
) -> tuple[list[tuple], list[tuple], list[tuple]]:
    """Run the three retrieval legs, optionally filtered to one regulation."""
    reg_clause = "AND metadata->>'regulation' = %s" if regulation else ""
    reg_param: tuple[str, ...] = (regulation,) if regulation else ()

    cur.execute(
        f"""
        SELECT id, document, metadata,
               1 - (embedding <=> %s::vector) AS score
        FROM embeddings
        WHERE TRUE {reg_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_embedding, *reg_param, query_embedding, fetch_k),
    )
    semantic_rows = cur.fetchall()

    cur.execute(
        f"""
        SELECT id, document, metadata,
               word_similarity(%s, document) AS score
        FROM embeddings
        WHERE TRUE {reg_clause}
        ORDER BY word_similarity(%s, document) DESC
        LIMIT %s
        """,
        (query, *reg_param, query, fetch_k),
    )
    keyword_rows = cur.fetchall()

    cur.execute(
        f"""
        SELECT id, document, metadata,
               word_similarity(%s,
                   COALESCE(metadata->>'article_number', '') || ' ' ||
                   COALESCE(metadata->>'title', '') || ' ' ||
                   COALESCE(metadata->>'regulation', '')
               ) AS score
        FROM embeddings
        WHERE TRUE {reg_clause}
        ORDER BY score DESC
        LIMIT %s
        """,
        (query, *reg_param, fetch_k),
    )
    metadata_rows = cur.fetchall()

    return semantic_rows, keyword_rows, metadata_rows


def _fuse(
    semantic_rows: list[tuple],
    keyword_rows: list[tuple],
    metadata_rows: list[tuple],
    top_k: int,
) -> list[RetrievedChunk]:
    rows_by_id: dict[str, tuple] = {}
    for row in semantic_rows + keyword_rows + metadata_rows:
        rows_by_id[row[0]] = row

    rrf_scores: dict[str, float] = {}
    for ranked_list in (semantic_rows, keyword_rows, metadata_rows):
        for rank, row in enumerate(ranked_list, start=1):
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


def _retrieve_filtered(
    cur: Any,
    query: str,
    query_embedding: list[float],
    top_k: int,
    regulation: str | None = None,
) -> list[RetrievedChunk]:
    fetch_k = top_k * 3
    semantic, keyword, metadata = _fetch_legs(cur, query, query_embedding, fetch_k, regulation)
    return _fuse(semantic, keyword, metadata, top_k)


def retrieve(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_embedding = embedder.embed([query])[0]
    regulations = _detect_regulations(query)

    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            if len(regulations) > 1:
                # Allocate slots evenly across detected regulations so each is
                # represented in the candidate set passed to the reranker.
                per_reg = top_k // len(regulations)
                remainder = top_k % len(regulations)
                chunks: list[RetrievedChunk] = []
                for i, reg in enumerate(regulations):
                    n = per_reg + (1 if i < remainder else 0)
                    chunks.extend(
                        _retrieve_filtered(cur, query, query_embedding, n, regulation=reg)
                    )
                return chunks
            else:
                return _retrieve_filtered(cur, query, query_embedding, top_k)

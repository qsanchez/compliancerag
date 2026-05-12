# ADR-003 — Hybrid Retrieval: semantic + keyword + re-ranking

**Status:** Accepted  
**Date:** 2026-05-08

## Decision

Use a three-stage retrieval pipeline for the pgvector backend:

1. **Semantic leg** — cosine similarity via pgvector (`<=>` operator) on Titan Embeddings v2 vectors.
2. **Keyword leg** — `pg_trgm` `word_similarity` on the raw document text (GIN trigram index).
3. **RRF fusion** — Reciprocal Rank Fusion (`k=60`, from the original RRF paper) merges ranked lists from both legs into a single fused ranking. Each leg fetches `top_k × 3` candidates before fusion, producing `top_k` fused results.
4. **Cross-encoder re-ranking** — the fused candidates are re-scored with `cross-encoder/ms-marco-MiniLM-L-6-v2` (lazy-loaded, toggled via `RERANKER_ENABLED`). The final `top_k=5` chunks are passed to the context builder.

Chroma (local dev) uses semantic-only retrieval; hybrid retrieval is a pgvector-only feature.

## Rationale

Regulatory text combines two distinct retrieval signals:

- **Semantic** — a question about "data minimisation obligations" should retrieve Article 5(1)(c) even if the exact phrase doesn't appear in the query.
- **Exact terminology** — a question citing "Article 32" or "Recital 83" must retrieve that specific article; semantic similarity alone can miss exact legal references in favour of topically related but wrong articles.

Pure semantic retrieval consistently missed exact article-number references in early RAGAS runs. Pure BM25 missed conceptual queries that didn't share surface vocabulary with the answer text. RRF requires no tuned weight between the two legs — rank position alone drives the score.

Cross-encoder re-ranking improves precision at the top-5 positions because it scores the full (query, passage) pair jointly, unlike the independent bi-encoder embeddings used in the semantic leg.

## Trade-off

Three-stage retrieval is slower than single-stage: two SQL queries + Python RRF + a local inference call (cross-encoder) add ~200–400 ms per query compared to a single pgvector lookup. For a compliance assistant where answer correctness matters more than sub-second latency, this is acceptable. The cross-encoder model is lazy-loaded and cached after the first call, so the overhead is amortised.

## Upgrade Path

If latency becomes a constraint, the cross-encoder can be replaced with a lighter model or a Bedrock Rerank API call (if available in the target region). The RRF `k` constant and `fetch_k` multiplier are tunable via config without changing the retrieval interface.

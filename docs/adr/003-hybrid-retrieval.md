# ADR-003 — Hybrid Retrieval: semantic + keyword + re-ranking

**Status:** Accepted (see Amendment below)  
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

---

## Amendment — 2026-05-16: Per-regulation retrieval for cross-regulation queries

**Status:** Accepted

### Problem

For queries that mention multiple regulations (e.g. "differences between GDPR and NIS2"),
the standard RRF retrieval consistently returned candidates from only one regulation.
The query embedding sits closest to whichever regulation dominates the corpus or whose
vocabulary best matches the query surface form — the other regulation is crowded out
before the reranker even sees it.

### Change

`retrieve()` detects regulation names in the query (`GDPR`, `NIS2`, `DORA`). When more
than one is found, it runs a separate three-leg RRF search **per regulation** (with a
`WHERE metadata->>'regulation' = %s` filter) and allocates retrieval slots evenly across
them. The combined candidate pool is then passed to the reranker as normal.

The pipeline's `_enforce_balance()` function applies a post-rerank quota: each detected
regulation is guaranteed `floor(top_k / n)` slots in the final context. Remaining slots
are filled in reranker rank order. Context size scales with the number of regulations:
4 chunks per regulation (single → 5, two → 8, three → 12).

### Why post-rerank balance is also needed

The reranker optimises for overall relevance to the query and can still select all chunks
from one regulation even after a balanced retrieval. The quota enforcement preserves the
reranker's quality judgement within each regulation while preventing full regulation
exclusion.

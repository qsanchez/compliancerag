# ADR-001 — Vector Store: pgvector over managed vector databases

**Status:** Accepted  
**Date:** 2026-05-08

## Decision

Use **pgvector on Amazon RDS PostgreSQL** as the production vector store, with **Chroma** as the local development alternative. The active backend is selected at runtime via the `VECTOR_STORE` environment variable (`chroma` | `pgvector`).

## Rationale

- **No vendor lock-in** — pgvector runs on standard PostgreSQL. Switching cloud providers or moving to a self-hosted DB requires no application code changes.
- **Hybrid retrieval in a single store** — `pg_trgm` trigram indexing lives in the same database, enabling semantic + keyword fusion (RRF) without a separate BM25 service.
- **SQL familiarity** — the analytics layer already uses PostgreSQL for the audit log; having vectors in the same DB simplifies joins and avoids cross-service query complexity.
- **Cost** — at PoC scale (~100K–500K document chunks), RDS PostgreSQL is significantly cheaper than managed vector databases (Pinecone, Weaviate, Qdrant) once their minimum-tier costs are factored in.
- **Local-first development** — Chroma provides the same retrieval interface via Docker Compose with zero AWS dependency during development.

## Trade-off

Managed vector databases (Pinecone, Weaviate) are more turnkey: automatic scaling, built-in ANN index tuning, and no RDS operational overhead. For a PoC targeting a single team, this is not worth the cost or lock-in. If the corpus grows beyond ~10M chunks or query concurrency demands sub-10ms p99 latency, revisiting a managed vector DB or switching to `pgvector` with HNSW indexing would be the first step.

## Upgrade Path

The `VECTOR_STORE=pgvector` path in `ingestion/indexer.py` and `rag/retriever.py` already uses `psycopg3` + the `pgvector` Python package directly. HNSW index creation can be added to `_ensure_pgvector_schema` in `ingestion/indexer.py` without changing the retrieval interface.

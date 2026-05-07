# ComplianceRAG — Claude Instructions

## Project
Hybrid RAG + Analytical Agent for regulatory compliance (GDPR, NIS2, DORA).
Full architecture in [ARCHITECTURE.md](ARCHITECTURE.md). Read it before starting any task.

## Stack (Phase 1)
- **Python 3.11+** with uv for dependency management
- **LiteLLM** → AWS Bedrock Claude 3 Haiku (generation)
- **AWS Bedrock Titan Embeddings v2** (embeddings)
- **Chroma** (local dev vector store) / **pgvector** (cloud)
- **LangGraph** (agent orchestration, Phase 3+)
- **FastAPI** (REST API)
- **RAGAS** (evaluation)
- **LangSmith** (observability)

## Repository layout
```
ingestion/   # document loaders, chunker, embedder, indexer, pipeline
rag/         # retriever, reranker, context_builder, prompts/
agent/       # LangGraph graph, router, tools/, state  (Phase 3)
api/         # FastAPI app, routers/, models, middleware/
analytics/   # ETL + Athena queries  (Phase 3)
evaluation/  # golden_dataset.json, evaluator, reports/
tests/       # unit/, integration/, regression/
infra/       # Terraform modules and environments
observability/
docs/adr/
```

## Local dev commands
```bash
task infra:up    # start Postgres/pgvector + Chroma via Docker Compose
task ingest      # run ingestion pipeline
task dev         # start FastAPI with hot reload (port 8000)
task test        # full test suite
task lint        # ruff linter
task format      # ruff formatter
task typecheck   # mypy
task eval        # RAGAS evaluation
```

## Code conventions
- Type hints on every function signature — no exceptions
- No comments unless the WHY is non-obvious (hidden constraint, workaround, subtle invariant)
- No docstrings beyond a single short line when truly needed
- `ruff` line-length = 100, targets = E, F, I, UP
- Async FastAPI handlers; sync elsewhere unless IO-bound
- Pydantic v2 models for all API request/response schemas
- Settings via `pydantic-settings` reading from `.env`

## Phased delivery — what is in scope now
**Phase 1 only.** Do not implement Phase 2–4 features unless explicitly asked.

### Phase 1 checklist
- [ ] `ingestion/sources/gdpr.py` — EUR-Lex loader, parse by article
- [ ] `ingestion/chunker.py` — recursive chunking by article/recital + metadata
- [ ] `ingestion/embedder.py` — Bedrock Titan Embeddings v2
- [ ] `ingestion/indexer.py` — Chroma indexing
- [ ] `ingestion/pipeline.py` — full pipeline orchestration
- [ ] `rag/retriever.py` — basic semantic retrieval from Chroma
- [ ] `rag/context_builder.py` — context assembly + citation formatting
- [ ] `rag/prompts/rag_system.txt` and `rag_user.txt`
- [ ] `api/main.py`, `api/routers/chat.py`, `api/routers/health.py`
- [ ] `api/models.py` — Pydantic request/response models
- [ ] `evaluation/golden_dataset.json` — 10 GDPR Q&A pairs
- [ ] `evaluation/evaluator.py` — RAGAS runner
- [ ] `tests/unit/` — chunker, embedder, retriever unit tests

## Key design constraints
- **Local-first:** Chroma + Docker Compose Postgres. No AWS required to develop and test.
- **Model-agnostic:** always go through LiteLLM, never call Bedrock SDK directly in business logic.
- **Evaluation-first:** every retrieval change needs a RAGAS delta. Golden dataset is the source of truth.
- **Auditability:** every query must log retrieved chunks, model version, prompt version, response.
- **Prompts are files:** `rag/prompts/*.txt` committed to Git, referenced by path — not inline strings.

## What NOT to do
- Do not add features beyond the current phase checklist
- Do not add error handling for impossible scenarios
- Do not inline prompt strings — always load from `rag/prompts/`
- Do not call AWS SDK directly in `rag/` or `api/` — use LiteLLM
- Do not commit `.env` (only `.env.example`)
- Do not push to `main` without running `task test` first

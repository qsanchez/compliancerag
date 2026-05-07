# ComplianceRAG — Claude Instructions

## Project
Hybrid RAG + Analytical Agent for regulatory compliance (GDPR, NIS2, DORA).
Full architecture, phased delivery plan, ADRs, and data sources in [ARCHITECTURE.md](ARCHITECTURE.md). Read it before starting any task.

## Stack
- **Python 3.11+** with uv for dependency management
- **LiteLLM** → AWS Bedrock Claude 3 Haiku/Sonnet (generation)
- **AWS Bedrock Titan Embeddings v2** (embeddings)
- **Chroma** (local dev) / **pgvector on RDS** (cloud) — vector stores
- **LangGraph** (agent orchestration, Phase 3)
- **FastAPI** (REST API)
- **RAGAS + LangSmith** (evaluation and observability)
- **Terraform** (IaC for all AWS resources)

## Repository layout
```
ingestion/       # loaders (gdpr/nis2/dora), chunker, embedder, indexer, pipeline
rag/             # retriever, reranker, context_builder, prompts/
agent/           # LangGraph graph, router, tools/, state  (Phase 3)
api/             # FastAPI app, routers/, models, middleware/
analytics/       # ETL loaders, Parquet schemas, Athena SQL queries  (Phase 3)
evaluation/      # golden_dataset.json, evaluator, reports/
tests/           # unit/, integration/, regression/
infra/           # Terraform modules (rds, s3, athena, lambda) + environments
observability/   # CloudWatch dashboards, LangSmith config
docs/adr/        # Architecture Decision Records
docs/diagrams/   # Mermaid architecture diagram  (Phase 4)
```

## Local dev commands
```bash
task infra:up          # start Postgres/pgvector + Chroma via Docker Compose
task ingest            # run ingestion pipeline
task dev               # start FastAPI with hot reload (port 8000)
task test              # full test suite
task test:unit         # unit tests only
task test:integration  # integration tests only
task lint              # ruff linter
task format            # ruff formatter
task typecheck         # mypy
task eval              # RAGAS evaluation
```

## Code conventions
- Type hints on every function signature — no exceptions
- No comments unless the WHY is non-obvious (hidden constraint, workaround, subtle invariant)
- No docstrings beyond a single short line when truly needed
- `ruff` line-length = 100, targets = E, F, I, UP
- Async FastAPI handlers; sync elsewhere unless IO-bound
- Pydantic v2 models for all API request/response schemas
- Settings via `pydantic-settings` reading from `.env`

## Key design constraints
- **Local-first:** Chroma + Docker Compose. No AWS required for Phase 1 development.
- **Model-agnostic:** always go through LiteLLM — never call Bedrock SDK directly in business logic.
- **Evaluation-first:** every retrieval change needs a RAGAS delta. Golden dataset is the source of truth.
- **Auditability:** every query must log retrieved chunks, model version, prompt version, response.
- **Prompts are files:** `rag/prompts/*.txt` committed to Git, loaded by path — never inline strings.

## What NOT to do
- Do not implement features from a future phase unless explicitly asked
- Do not add error handling for impossible scenarios
- Do not inline prompt strings — always load from `rag/prompts/`
- Do not call AWS SDK directly in `rag/` or `api/` — use LiteLLM
- Do not commit `.env` (only `.env.example`)
- Do not push to `main` without running `task test` first
- Do not invoke `uv run`, `pytest`, `ruff`, or `mypy` directly — always use the `task` commands above

# ComplianceRAG — Claude Instructions

## Project
Hybrid RAG + Analytical Agent for regulatory compliance (GDPR, NIS2, DORA).
Full architecture, ADRs, and data sources in [ARCHITECTURE.md](ARCHITECTURE.md). Read it before starting any task.

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
task infra:up    # start Postgres/pgvector + Chroma via Docker Compose
task ingest      # run ingestion pipeline
task dev         # start FastAPI with hot reload (port 8000)
task test        # full test suite
task lint        # ruff linter
task format      # ruff formatter
task typecheck   # mypy
task eval        # RAGAS evaluation
```

## Phased delivery

### Phase 1 — Core RAG
**Exit criterion:** RAGAS faithfulness ≥ 0.7 on 10-question GDPR golden dataset.
- [x] Project scaffolding
- [ ] GDPR loader (EUR-Lex, parse by article)
- [ ] Chunker — recursive by article/recital + metadata
- [ ] Embedder — Bedrock Titan Embeddings v2
- [ ] Indexer — Chroma (local dev)
- [ ] Pipeline — orchestrates full ingestion
- [ ] Retriever — basic semantic retrieval from Chroma
- [ ] Context builder — context assembly + citation formatting
- [ ] Prompt templates — `rag/prompts/rag_system.txt` + `rag_user.txt`
- [ ] FastAPI `/chat` and `/health` endpoints (minimal)
- [ ] Pydantic request/response models
- [ ] Golden dataset — 10 GDPR Q&A pairs
- [ ] RAGAS evaluator runner
- [ ] Unit tests — chunker, embedder, retriever

### Phase 2 — Corpus expansion + Hybrid Retrieval
**Exit criterion:** RAGAS hybrid ≥ Phase 1 baseline; LangSmith traces visible.
- [ ] NIS2 + DORA loaders
- [ ] pgvector on RDS (Terraform `modules/rds`)
- [ ] Hybrid retrieval: pgvector semantic + pg_trgm keyword
- [ ] Cross-encoder re-ranking
- [ ] LangSmith tracing on every query
- [ ] Golden dataset expanded to 30 questions (GDPR + NIS2 + DORA)
- [ ] RAGAS comparison: Phase 1 baseline vs hybrid

### Phase 3 — Agentic + Analytics
**Exit criterion:** Agent routes RAG vs analytics correctly; charts render end-to-end.
- [ ] LangGraph router agent (`agent/graph.py`, `agent/router.py`, `agent/state.py`)
- [ ] `search_regulations` tool (wraps RAG pipeline)
- [ ] GDPR fines dataset → S3 Parquet
- [ ] Athena workgroup + database (Terraform `modules/athena`)
- [ ] `query_metrics` tool (Athena SQL)
- [ ] `generate_chart` tool (matplotlib/plotly → base64)
- [ ] Multi-turn conversation state
- [ ] Prompt injection defense
- [ ] Agent regression test suite

### Phase 4 — Production Hardening
**Exit criterion:** One-command AWS deploy; CI green on every PR; CloudWatch dashboard live.
- [ ] FastAPI: API key auth, rate limiting, structured logging, error handling
- [ ] Audit logging (user, timestamp, chunks, model version, response)
- [ ] Lambda + API Gateway (Terraform `modules/lambda`)
- [ ] CloudWatch dashboard: latency, cost/query, error rate
- [ ] GitHub Actions CI: tests + RAGAS eval on PR; tf-plan on infra PR
- [ ] Architecture diagram (Mermaid) in `docs/diagrams/`
- [ ] ADRs complete

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

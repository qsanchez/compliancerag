# ComplianceRAG — Architecture Document

> **Hybrid RAG + Analytical Agent for Regulatory Compliance**  
> Version: 1.0 — All phases complete  
> Status: Phases 1–7 complete

---

## 1. Project Overview

### What it is

ComplianceRAG is an enterprise-grade AI assistant that answers questions about regulatory compliance (GDPR, NIS2, DORA) combining two capabilities:

- **Textual Q&A via RAG** — answers grounded in the actual normative text, with exact citations to articles and recitals
- **Quantitative analysis via structured data** — answers about enforcement trends, fines, incident statistics over time, with charts

### Why it exists

To demonstrate production-ready GenAI architecture skills: RAG pipeline design, hybrid retrieval, context engineering, agentic orchestration, evaluation-driven development, LLMOps, and GenAI observability — all on AWS.

### Target audience (for the PoC)

- Compliance officers asking "what does Article 32 of GDPR require?"
- Risk managers asking "what has been the trend of GDPR fines in Spain over the last 3 years?"
- Security architects asking "what are the NIS2 obligations for cloud providers?"

---

## 2. Architecture Overview

### 2.1 Context Diagram
![Context Diagram](docs/diagrams/context.svg)

### 2.2 Data Flow Diagram
![Data Flow Diagram](docs/diagrams/data-flow.svg)

### 2.3 Infrastructure Diagram
![Infrastructure Diagram](docs/diagrams/infra.svg)

### 2.4 Module Dependency Diagram
![Module Dependency Diagram](docs/diagrams/code.svg)

---

## 3. Stack

| Layer | Technology | Rationale |
|---|---|---|
| LLM | AWS Bedrock — Claude Haiku 4.5 | AWS-native, production-grade, no GPU management |
| Embeddings | AWS Bedrock — Amazon Titan Embeddings v2 | AWS-native, consistent with Bedrock setup |
| LLM abstraction | LiteLLM | Model-agnostic interface — swap models without code changes |
| Orchestration | LangGraph | Stateful agent with explicit routing graph; author's existing expertise |
| Vector store | pgvector on Amazon RDS PostgreSQL | Production-grade, no vendor lock-in, supports hybrid retrieval |
| Hybrid retrieval | pgvector (semantic) + pg_trgm (BM25-like) + re-ranking | Best of both worlds: semantic + keyword |
| Analytical data | Amazon S3 + Athena | Serverless SQL over Parquet; minimal cost; enterprise pattern |
| API | FastAPI + Mangum | Lightweight, async, OpenAPI docs out of the box; Mangum adapts to Lambda |
| Serving (cloud) | AWS Lambda + API Gateway | Sufficient for PoC traffic; see ADR-006 for future Fargate path |
| IaC | Terraform | Cloud-agnostic; consistent with multi-cloud architect profile |
| CI/CD | GitHub Actions | Regression tests, RAGAS eval, Terraform plan on every PR |
| Evaluation | RAGAS | Faithfulness, answer relevancy, context precision/recall |
| LLM Observability | LangSmith | Traces, prompt versioning, experiment tracking |
| Infra Observability | AWS CloudWatch | Metrics, cost alerts, latency dashboards |

---

## 4. Repository Structure

```
compliancerag/
│
├── infra/                          # Terraform
│   ├── modules/
│   │   ├── networking/             # VPC + private subnets + route tables
│   │   ├── rds/                    # RDS PostgreSQL + pgvector
│   │   ├── s3/                     # S3 buckets (documents + analytics data)
│   │   ├── athena/                 # Athena workgroup + databases
│   │   ├── lambda/                 # Lambda function + ECR
│   │   ├── api_gateway/            # HTTP API + JWT authorizer
│   │   ├── cognito/                # User Pool + Hosted UI
│   │   ├── frontend/               # S3 + CloudFront distribution
│   │   └── cloudwatch/             # Dashboard + metric filters + alarms
│   ├── environments/
│   │   ├── local.tfvars
│   │   └── prod.tfvars
│   └── main.tf
│
├── ingestion/                      # Document ingestion pipeline
│   ├── sources/                    # Source-specific loaders
│   │   ├── gdpr.py                 # GDPR full text loader (EUR-Lex)
│   │   ├── nis2.py                 # NIS2 directive loader
│   │   └── dora.py                 # DORA regulation loader
│   ├── chunker.py                  # Token sliding window chunking
│   ├── indexer.py                  # pgvector write operations
│   └── pipeline.py                 # Orchestrates full ingestion run
│
├── vectorstore/                    # Shared vector DB access layer
│   ├── embedder.py                 # Embedding via Bedrock Titan
│   └── client.py                   # pgvector connection + schema
│
├── rag/                            # RAG pipeline
│   ├── pipeline.py                 # Full pipeline: retrieve → rerank → build → generate
│   ├── retriever.py                # Hybrid retrieval (semantic + BM25 + RRF)
│   ├── reranker.py                 # Cross-encoder re-ranking
│   ├── context_builder.py          # Context assembly + citation formatting
│   └── prompts/                    # Prompt templates (versioned)
│       ├── rag_system.txt
│       └── rag_user.txt
│
├── agent/                          # LangGraph agent
│   ├── graph.py                    # Agent graph definition
│   ├── router.py                   # RAG vs Analytics routing logic
│   ├── sanitizer.py                # Prompt injection defence
│   └── state.py                    # Agent state schema
│
├── analytics_etl/                  # Enforcement data — load side
│   ├── datasets/                   # Raw public datasets (CSV)
│   ├── schemas/                    # Parquet schemas
│   ├── loaders/                    # ETL: CSV → Parquet → S3
│   └── queries/                    # Named Athena SQL queries
│
├── analytics_query/                # Enforcement data — read side
│   ├── query_metrics.py            # Athena SQL tool (LLM-generated SQL)
│   ├── generate_chart.py           # matplotlib chart → base64
│   └── prompts/
│       └── sql_system.txt
│
├── api/                            # FastAPI application
│   ├── main.py                     # App factory + Mangum Lambda handler
│   ├── routers/
│   │   ├── chat.py                 # /chat endpoint
│   │   └── health.py               # /health endpoint
│   ├── models.py                   # Pydantic request/response models
│   └── middleware/
│       ├── auth.py                 # API key auth
│       └── logging.py              # Structured logging
│
├── audit/                          # Compliance audit trail
│   └── logger.py                   # Writes every query to Postgres audit_log
│
├── evaluation/                     # RAGAS evaluation
│   ├── golden_dataset.json         # Ground truth Q&A pairs
│   ├── evaluator.py                # RAGAS runner
│   └── reports/                    # Evaluation outputs (gitignored)
│
├── observability/                  # Monitoring config
│   ├── cloudwatch/                 # Dashboard definitions (JSON)
│   └── langsmith/                  # LangSmith project config
│
├── tests/
│   ├── unit/                       # Unit tests (all modules, mocked deps)
│   └── integration/                # Integration tests (real infra)
│
├── docs/
│   ├── adr/                        # Architecture Decision Records
│   └── diagrams/
│
├── docker-compose.yml              # Local dev: Postgres + pgvector
├── Taskfile.yml                    # Task runner (see section 8)
├── pyproject.toml
├── .env.example
└── .github/
    └── workflows/
        ├── ci.yml                  # Tests + RAGAS eval on PR
        └── tf-validate.yml         # Terraform fmt + validate on infra PR
```

---

## 5. Data Sources

### Regulatory text (RAG corpus)
| Source | Format | URL |
|---|---|---|
| GDPR full text | HTML (per-article) | https://gdpr-info.eu — EUR-Lex blocks programmatic access via AWS WAF; gdpr-info.eu republishes the official text structured by article |
| NIS2 Directive | HTML (full text) | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022L2555 |
| DORA Regulation | HTML (full text) | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R2554 |

### Quantitative enforcement data (Analytics)
| Source | Content | Format |
|---|---|---|
| GDPR Enforcement Tracker (enforcementtracker.com) | All GDPR fines by country, company, article, date | CSV (public) |
| ENISA Threat Landscape reports | Incident statistics by sector and year | PDF/structured |
| ICO / AEPD public registers | National DPA decisions | CSV/JSON |

---

## 6. Phased Delivery Plan

### Phase 1 — Core RAG (complete)
**Goal:** Working RAG pipeline answering textual questions about GDPR with citations.  
**Exit criterion:** RAGAS faithfulness ≥ 0.7 on 10-question golden dataset.

- [x] Project scaffolding (structure, pyproject.toml, docker-compose, .env.example, Taskfile)
- [x] GDPR document loader — fetch from gdpr-info.eu, parse by article and recital
- [x] Chunking strategy — token sliding window (512 tokens, 50 overlap), with metadata
- [x] Embedding via Bedrock Titan Embeddings v2
- [x] Basic semantic retrieval
- [x] Context builder with citation formatting
- [x] Prompt templates (system + user)
- [x] LiteLLM wrapper around Bedrock Claude Haiku 4.5
- [x] FastAPI `/chat` endpoint (minimal)
- [x] 10-question golden dataset for GDPR
- [x] RAGAS baseline — faithfulness 0.886, answer_relevancy 0.878, context_precision 0.733, context_recall 0.886
- [x] Unit tests for chunker, embedder, retriever

### Phase 2 — Corpus Expansion + Hybrid Retrieval (complete)
**Goal:** Extend corpus to all 3 regulations; replace pure semantic retrieval with hybrid + re-ranking; add full observability.  
**Exit criterion:** RAGAS comparison shows hybrid ≥ Phase 1 baseline; LangSmith traces visible for every query.

- [x] NIS2 + DORA loaders — 46 NIS2 articles + 64 DORA articles via EUR-Lex HTML parser
- [x] pgvector on RDS PostgreSQL (Terraform `modules/rds`)
- [x] Hybrid retrieval: semantic (pgvector) + keyword (pg_trgm) + metadata (article_number + title) with RRF fusion (k=60) — three legs, each fetching `top_k × 3` candidates
- [x] Cross-encoder re-ranking — `ms-marco-MiniLM-L-6-v2` implemented; replaced by LLM reranker (Claude via LiteLLM) in Phase 7 (see ADR-009)
- [x] LangSmith integration — `@traceable` on retrieve/rerank/pipeline
- [x] Expand golden dataset to 30 questions across GDPR, NIS2, DORA
- [x] RAGAS evaluation comparison: Phase 1 baseline vs hybrid retrieval

### Phase 3 — Agentic + Analytics (complete)
**Goal:** LangGraph router that decides between RAG and quantitative analytics; charts over enforcement data.  
**Exit criterion:** Agent correctly routes RAG vs analytics queries; time-series charts render end-to-end.

- [x] LangGraph agent with router node (`agent/graph.py`, `agent/router.py`)
- [x] RAG pipeline unified in `rag/pipeline.py` (retrieve → rerank → build → generate)
- [x] GDPR fines dataset loaded to S3 as Parquet
- [x] Athena workgroup + database (Terraform `modules/athena`)
- [x] `query_metrics` tool (LLM-generated Athena SQL with injection guard)
- [x] `generate_chart` tool (matplotlib → base64)
- [x] Agent state for multi-turn conversation
- [x] Prompt injection defence (`agent/sanitizer.py`)
- [x] Unit tests for all agent and analytics_query modules

### Phase 4 — Production Hardening (complete)
**Goal:** Deployable to AWS with full observability, CI/CD, and audit trail.  
**Exit criterion:** CI green on every PR; one-command deploy to AWS; CloudWatch dashboard live.

- [x] Structured logging (structlog JSON) and error handling
- [x] API key auth middleware
- [x] Audit logging — every query written to Postgres `audit_log`
- [x] AWS Lambda + API Gateway (Terraform `modules/lambda` + `modules/api_gateway`)
- [x] GitHub Actions CI: lint, format, typecheck, unit tests on every PR
- [x] ADRs complete (`docs/adr/` — 001–009)
- [x] CloudWatch dashboard: latency, cost per query, error rate

### Phase 5 — Integration Tests + Analytics Extract (complete)
**Goal:** Confidence that the full stack works end-to-end against real infrastructure; real enforcement data flowing through the analytics pipeline.  
**Exit criterion:** All integration tests green with local infra running; real GDPR fines data downloaded and queryable via Athena.

- [x] Integration tests (`tests/integration/`) — 6 test files split by infrastructure dependency:
  - `test_indexer.py` + `test_audit_logger.py` — local infra only (`task local_infra:up`)
  - `test_retriever.py` + `test_pipeline.py` — require AWS Bedrock + pgvector with data loaded
  - `test_query_metrics.py` — requires Athena + analytics data loaded
  - `test_api.py` — requires running API (`task api:up`)
- [x] Analytics extract (`analytics_etl/extract/gdpr_fines.py`) — fetches 3,100+ real fines from the enforcementtracker.com internal JSON feed, normalises to schema, saves to `analytics_etl/datasets/gdpr_fines_raw.csv`
- [x] `task analytics:extract` wired up as prerequisite to `task analytics:load`
- [x] Real GDPR fines data (3,142 rows) loaded to S3 and queryable via Athena

### Phase 6 — Frontend Chat UI (complete)
**Goal:** Browser-based chat interface with Cognito authentication, suggested prompts, and inline chart rendering.  
**Exit criterion:** Authenticated users can ask questions and see answers with citations and charts via a CloudFront URL.

- [x] `infra/modules/frontend/` — S3 bucket + CloudFront distribution (OAC, HTTPS, SPA routing)
- [x] `infra/modules/cognito/` — Cognito User Pool + App Client + Hosted UI domain
- [x] API Gateway JWT authorizer — validates Cognito access tokens on `/chat` route
- [x] `frontend/index.html` + `app.js` + `style.css` — vanilla JS SPA: chat bubbles, suggested prompts, base64 chart rendering
- [x] `frontend/config.template.js` + `task frontend:config` — generates `config.js` from Terraform outputs
- [x] `task frontend:deploy` — syncs assets to S3 + CloudFront cache invalidation

### Phase 7 — us-east-1 Migration + LLM Reranking + Retrieval Diversity (complete)
**Goal:** Migrate production from eu-west-1 to us-east-1; replace the Lambda-incompatible PyTorch cross-encoder with a managed reranker; fix multi-regulation retrieval quality.  
**Exit criterion:** Full pipeline running in us-east-1 with `RERANKER_ENABLED=true`; RAGAS Phase 5 evaluation confirms improvement over Phase 2 baseline.

- [x] Migrated deployment from eu-west-1 to us-east-1 — updated `prod.tfvars`, Bedrock model prefix (`eu.` → `us.`), re-applied Terraform
- [x] Built and pushed new Docker image to us-east-1 ECR repository
- [x] Re-ingested GDPR, NIS2, DORA into us-east-1 RDS
- [x] Re-loaded analytics Parquet to us-east-1 S3 bucket
- [x] `rag/reranker.py` — replaced PyTorch `CrossEncoder` with LLM reranker: single `litellm.completion` call to Claude Haiku, returns JSON-ranked indices; fallback to vector-similarity order on failure (Cohere Rerank v3.5 was inaccessible — AWS Marketplace subscription wall; see ADR-009)
- [x] Per-regulation retrieval diversity — `_detect_regulations()` detects regulation names in query; separate RRF search per regulation with `WHERE metadata->>'regulation' = %s` filter; slots allocated evenly across detected regulations
- [x] Post-rerank balance enforcement — `_enforce_balance()` guarantees minimum quota per regulation in the final context window; context size scales with regulation count (`_TOP_K_PER_REG = 4`: single → 5, two → 8, three → 12 chunks)
- [x] CI fixed — GitHub Actions runs `pytest tests/unit/` only; integration tests require live DB + Bedrock and must be run manually
- [x] RAGAS Phase 5 evaluation — 30 questions across GDPR/NIS2/DORA: faithfulness 0.98, answer_relevancy 0.91, context_precision 0.83, context_recall 0.85
- [x] Metrics evolution chart (`evaluation/reports/metrics_evolution.svg`) committed to repository

---

## 7. Architecture Decision Records (ADRs)

### ADR-001 — Vector Store: pgvector over managed vector databases
**Decision:** pgvector on RDS PostgreSQL as the single vector store (local dev and production).  
**Rationale:** Production-grade, no vendor lock-in, native hybrid retrieval via pg_trgm. Since Postgres is already required for audit logging, running a second vector DB locally adds cost with no benefit.  
**Trade-off:** Less turnkey than managed vector DBs; requires RDS management. Acceptable given Terraform IaC.

### ADR-002 — LLM Provider: AWS Bedrock
**Decision:** AWS Bedrock with Claude Haiku 4.5 (default) / Sonnet (complex queries).  
**Rationale:** AWS-native, no GPU management, pay-per-token, enterprise security posture (VPC, IAM, no data retention). Consistent with AWS-first architecture.  
**Trade-off:** Requires explicit model access activation per region. Mitigated by LiteLLM abstraction.

### ADR-003 — Hybrid Retrieval: semantic + keyword + LLM re-ranking + diversity
**Decision:** Combine pgvector semantic search with pg_trgm keyword search, fused with RRF, then re-rank with an LLM reranker (Claude via LiteLLM). For multi-regulation queries, per-regulation retrieval and post-rerank balance enforcement guarantee representation from each regulation.  
**Rationale:** Regulatory text has both semantic content (concepts, obligations) and exact terminology (article numbers, defined terms). Re-ranking improves precision; per-regulation retrieval prevents one regulation from crowding out others in multi-regulation queries.  
**Trade-off:** Higher latency than single-stage retrieval. Acceptable for compliance use case where precision > speed.

### ADR-004 — Agent Framework: LangGraph
**Decision:** LangGraph for agent orchestration.  
**Rationale:** Explicit graph-based control flow is essential for a router that decides between RAG and analytics paths. Stateful, inspectable, testable — critical for regulated environments requiring auditability.  
**Trade-off:** More verbose than simple LangChain chains. The explicitness is a feature in this context.

### ADR-005 — Chunking Strategy: Recursive Character Splitting (Phase 1)
**Decision:** Recursive character splitting (512 tokens, 50-token overlap) for Phase 1.  
**Rationale:** Zero extra dependencies, fast, deterministic. Sufficient to validate the pipeline before optimising retrieval quality.  
**Trade-off:** Structure-blind — chunk boundaries may fall mid-obligation. To be revisited with semantic chunking if RAGAS scores plateau.

### ADR-009 — Reranker Infrastructure: LLM reranker over local inference
**Decision:** Replace local `cross-encoder/ms-marco-MiniLM-L-6-v2` with an LLM-based reranker: a single `litellm.completion` call to Claude Haiku that receives all candidate chunks and returns a JSON-ranked index array.  
**Rationale:** PyTorch JIT warm-up takes 30–60 s on Lambda's ARM64 CPU — consistently hitting the 60 s timeout. Cohere Rerank v3.5 via Bedrock was the original plan but proved inaccessible (requires an AWS Marketplace subscription that cannot be activated via API, CLI, or console; the Bedrock playground is disabled for reranking models). The LLM reranker uses existing Bedrock access, adds no new AWS resources, and uses chunk metadata (regulation, article, title) in its relevance judgement — which pure cross-encoders ignore.  
**Trade-off:** One additional LLM call per query (~300–500 ms, ~500 tokens). Acceptable given reranking quality; fallback to vector-similarity order on any exception ensures no hard dependency.

---

## 8. Local Development

### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- AWS CLI configured (for Bedrock calls)
- LangSmith account (free tier)

### Quick start

```bash
git clone https://github.com/<your-handle>/compliancerag
cd compliancerag
cp .env.example .env          # fill in AWS credentials + LangSmith API key

task local_infra:up           # start Postgres + pgvector
uv sync                       # install dependencies

task ingest                   # ingest GDPR documents
task api:up                   # start API on :8000

task eval                     # run RAGAS evaluation
task test:unit                # run unit tests
```

### Task reference

| Task | Description |
|---|---|
| `task ingest` | Run ingestion pipeline (default: GDPR) |
| `task eval` | Run RAGAS evaluation |
| `task test` | Full test suite |
| `task test:unit` | Unit tests only |
| `task test:integration` | Integration tests (requires running infra) |
| `task lint` / `task format` / `task typecheck` | Code quality |
| `task api:up` / `task api:down` | Start / stop local API |
| `task local_infra:up` / `task local_infra:down` | Start / stop Docker Compose |
| `task cloud_infra:init` | Terraform init |
| `task cloud_infra:plan` | Terraform plan (ENV=local\|prod) |
| `task cloud_infra:apply` | Terraform apply (ENV=local\|prod) |
| `task cloud_infra:destroy` | Terraform destroy |
| `task app:build` | Build Lambda container image |
| `task app:push` | Push image to ECR |
| `task app:deploy` | Update Lambda function |
| `task analytics:extract` | Download real enforcement CSV files *(Phase 5)* |
| `task analytics:load` | Convert CSV → Parquet → S3 |

---

## 9. Environment Variables

```bash
# AWS
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
BEDROCK_MODEL_ID=eu.anthropic.claude-haiku-4-5-20251001-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# Vector store (pgvector)
DATABASE_URL=postgresql://compliancerag:compliancerag@localhost:5432/compliancerag

# Analytics
ATHENA_DATABASE=compliancerag
ATHENA_TABLE_FINES=gdpr_fines
ATHENA_S3_OUTPUT=s3://...          # terraform output athena_s3_output
ATHENA_S3_DATA_BUCKET=...          # terraform output analytics_data_bucket

# LLMOps
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=compliancerag
LANGCHAIN_TRACING_V2=true

# Reranker (disabled on Lambda — CPU inference too slow; enable on ECS)
RERANKER_ENABLED=false
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# API
API_KEY=                           # simple API key auth for PoC
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 10. Key Design Principles

1. **Evaluation-first** — RAGAS runs on every PR. No retrieval change ships without measured quality delta.
2. **Auditability** — every query is logged with retrieved chunks, model version, prompt version, and response. Regulatory context demands traceability.
3. **Model-agnostic via LiteLLM** — Bedrock today, OpenAI or Azure OpenAI tomorrow. One line change.
4. **IaC everything** — no manual AWS console operations. Reproducible infra via Terraform.
5. **Local-first development** — single Postgres instance (pgvector + audit log) via Docker Compose. No AWS required to develop and test the RAG pipeline.
6. **Prompt versioning** — prompts are files, committed to Git, referenced by version in LangSmith traces.

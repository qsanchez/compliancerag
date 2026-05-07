# ComplianceRAG — Architecture Document

> **Hybrid RAG + Analytical Agent for Regulatory Compliance**  
> Version: 0.1 — Initial  
> Status: Phase 2 in progress

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

```
┌─────────────────────────────────────────────────────────────┐
│                        User / API Client                     │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────┐
│                     FastAPI — REST API                       │
│              (AWS Lambda + API Gateway / ECS Fargate)        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   LangGraph Agent (Router)                   │
│                                                             │
│   ┌─────────────────┐         ┌───────────────────────┐    │
│   │  RAG Tool        │         │  Analytics Tool        │    │
│   │  search_regs()   │         │  query_metrics()       │    │
│   └────────┬────────┘         └──────────┬────────────┘    │
│            │                             │                   │
└────────────┼─────────────────────────────┼───────────────────┘
             │                             │
┌────────────▼──────────┐   ┌─────────────▼──────────────────┐
│   RAG Pipeline         │   │   Analytics Pipeline            │
│                        │   │                                 │
│  pgvector (RDS PG)     │   │  Amazon Athena + S3 (Parquet)  │
│  Hybrid retrieval      │   │  GDPR/NIS2 enforcement data     │
│  BM25 + semantic       │   │  Time series, fines, stats      │
│  Re-ranking            │   │                                 │
└────────────┬──────────┘   └─────────────┬──────────────────┘
             │                             │
┌────────────▼─────────────────────────────▼──────────────────┐
│               AWS Bedrock                                    │
│   Claude 3 Haiku/Sonnet (generation)                        │
│   Amazon Titan Embeddings v2 (embeddings)                   │
└─────────────────────────────────────────────────────────────┘
             │
┌────────────▼──────────────────────────────────────────────  ┐
│               Observability & LLMOps                         │
│   LangSmith — traces, prompt versioning, evaluation          │
│   AWS CloudWatch — infra metrics, cost, latency              │
│   RAGAS — RAG quality evaluation                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Stack

| Layer | Technology | Rationale |
|---|---|---|
| LLM | AWS Bedrock — Claude 3 Haiku/Sonnet | AWS-native, production-grade, no GPU management |
| Embeddings | AWS Bedrock — Amazon Titan Embeddings v2 | AWS-native, consistent with Bedrock setup |
| LLM abstraction | LiteLLM | Model-agnostic interface — swap models without code changes |
| Orchestration | LangGraph | Stateful agent with explicit routing graph; author's existing expertise |
| Vector store | pgvector on Amazon RDS PostgreSQL | Production-grade, no vendor lock-in, supports hybrid retrieval |
| Vector store (local dev) | Chroma | Same interface as pgvector wrapper, zero infra for fast iteration |
| Hybrid retrieval | pgvector (semantic) + pg_trgm (BM25-like) + re-ranking | Best of both worlds: semantic + keyword |
| Analytical data | Amazon S3 + Athena | Serverless SQL over Parquet; minimal cost; enterprise pattern |
| API | FastAPI | Lightweight, async, OpenAPI docs out of the box |
| Serving (cloud) | AWS Lambda + API Gateway OR ECS Fargate | Lambda for low-traffic PoC; Fargate for production path |
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
│   │   ├── rds/                    # RDS PostgreSQL + pgvector
│   │   ├── s3/                     # S3 buckets (documents + analytics data)
│   │   ├── athena/                 # Athena workgroup + databases
│   │   └── lambda/                 # Lambda + API Gateway (optional)
│   ├── environments/
│   │   ├── local.tfvars            # Local dev overrides
│   │   └── prod.tfvars             # Cloud deployment
│   └── main.tf
│
├── ingestion/                      # Document ingestion pipeline
│   ├── sources/                    # Source-specific scrapers/loaders
│   │   ├── gdpr.py                 # GDPR full text loader (EUR-Lex)
│   │   ├── nis2.py                 # NIS2 directive loader
│   │   └── dora.py                 # DORA regulation loader
│   ├── chunker.py                  # Chunking strategies (recursive, semantic)
│   ├── embedder.py                 # Embedding via Bedrock Titan
│   ├── indexer.py                  # pgvector / Chroma indexing
│   └── pipeline.py                 # Orchestrates full ingestion run
│
├── rag/                            # RAG pipeline
│   ├── retriever.py                # Hybrid retrieval (semantic + BM25 + rerank)
│   ├── reranker.py                 # Cross-encoder re-ranking
│   ├── context_builder.py          # Context assembly + citation formatting
│   └── prompts/                    # Prompt templates (versioned)
│       ├── rag_system.txt
│       └── rag_user.txt
│
├── agent/                          # LangGraph agent
│   ├── graph.py                    # Agent graph definition
│   ├── router.py                   # RAG vs Analytics routing logic
│   ├── tools/
│   │   ├── search_regulations.py   # RAG tool
│   │   ├── query_metrics.py        # Athena analytics tool
│   │   └── generate_chart.py       # Chart generation tool
│   └── state.py                    # Agent state schema
│
├── api/                            # FastAPI application
│   ├── main.py
│   ├── routers/
│   │   ├── chat.py                 # /chat endpoint
│   │   └── health.py               # /health endpoint
│   ├── models.py                   # Pydantic request/response models
│   └── middleware/
│       ├── auth.py                 # API key auth
│       └── logging.py              # Structured logging
│
├── analytics/                      # Quantitative data layer
│   ├── datasets/                   # Raw public datasets (GDPR fines, NIS2 incidents)
│   ├── schemas/                    # Parquet schemas
│   ├── loaders/                    # ETL: CSV/JSON → Parquet → S3
│   └── queries/                    # Named Athena SQL queries
│
├── evaluation/                     # RAGAS evaluation
│   ├── golden_dataset.json         # Ground truth Q&A pairs
│   ├── evaluator.py                # RAGAS runner
│   └── reports/                    # Evaluation outputs (gitignored, except summaries)
│
├── observability/                  # Monitoring config
│   ├── cloudwatch/                 # Dashboard definitions (JSON)
│   └── langsmith/                  # LangSmith project config
│
├── tests/                          # Test suite
│   ├── unit/                       # Unit tests per module
│   ├── integration/                # End-to-end pipeline tests
│   └── regression/                 # Prompt/agent regression suite (CI)
│
├── docs/                           # Architecture decisions
│   ├── adr/
│   │   ├── 001-vector-store.md
│   │   ├── 002-llm-provider.md
│   │   ├── 003-hybrid-retrieval.md
│   │   └── 004-agent-framework.md
│   └── diagrams/
│
├── docker-compose.yml              # Local dev: Postgres + pgvector + Chroma
├── Makefile                        # make ingest / make eval / make test / make deploy
├── pyproject.toml                  # Dependencies (uv or poetry)
├── .env.example                    # Env vars template
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Tests + RAGAS eval on PR
│       └── tf-plan.yml             # Terraform plan on infra PR
└── ARCHITECTURE.md                 # This file
```

---

## 5. Data Sources

### Regulatory text (RAG corpus)
| Source | Format | URL |
|---|---|---|
| GDPR full text | HTML (per-article) | https://gdpr-info.eu — EUR-Lex blocks programmatic access via AWS WAF; gdpr-info.eu republishes the official text structured by article |
| NIS2 Directive | HTML (full text) | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022L2555 — EUR-Lex accessible locally with browser headers (blocked from AWS) |
| DORA Regulation | HTML (full text) | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R2554 — same as NIS2 |

### Quantitative enforcement data (Analytics)
| Source | Content | Format |
|---|---|---|
| GDPR Enforcement Tracker (enforcementtracker.com) | All GDPR fines by country, company, article, date | CSV (public) |
| ENISA Threat Landscape reports | Incident statistics by sector and year | PDF/structured |
| ICO / AEPD public registers | National DPA decisions | CSV/JSON |

---

## 6. Phased Delivery Plan

### Phase 1 — Core RAG (target: 1-2 weeks)
**Goal:** Working RAG pipeline answering textual questions about GDPR with citations.  
**Exit criterion:** RAGAS faithfulness ≥ 0.7 on 10-question golden dataset.

- [x] Project scaffolding (structure, pyproject.toml, docker-compose, .env.example, Taskfile)
- [x] GDPR document loader — fetch from gdpr-info.eu, parse by article and recital
- [x] Chunking strategy — token sliding window (512 tokens, 50 overlap), with metadata (article_number, regulation, chapter)
- [x] Embedding via Bedrock Titan Embeddings v2
- [x] Chroma vector store for local dev
- [x] Basic semantic retrieval
- [x] Context builder with citation formatting
- [x] Prompt templates (system + user)
- [x] LiteLLM wrapper around Bedrock Claude Haiku 4.5
- [x] FastAPI `/chat` endpoint (minimal)
- [x] 10-question golden dataset for GDPR
- [x] RAGAS baseline evaluation run — faithfulness 0.886, answer_relevancy 0.878, context_precision 0.733, context_recall 0.886
- [x] Unit tests for chunker, embedder, retriever

### Phase 2 — Corpus expansion + Hybrid Retrieval (target: 1-2 weeks)
**Goal:** Extend corpus to all 3 regulations; replace pure semantic retrieval with hybrid + re-ranking; add full observability.  
**Exit criterion:** RAGAS comparison shows hybrid ≥ Phase 1 baseline; LangSmith traces visible for every query.

- [x] NIS2 + DORA loaders added to corpus — 46 NIS2 articles + 64 DORA articles via EUR-Lex HTML full-text parser
- [x] pgvector on RDS PostgreSQL (Terraform `modules/rds`) — RDS module + pgvector code path in indexer/retriever, switchable via `VECTOR_STORE=pgvector`
- [x] Hybrid retrieval: semantic (pgvector) + keyword (pg_trgm / BM25-like) — RRF fusion (k=60); GIN trigram index on document column
- [x] Cross-encoder re-ranking — `sentence-transformers` `CrossEncoder` (ms-marco-MiniLM-L-6-v2); lazy-loaded; wired into chat router + evaluator; fetch_k = 3×top_k candidates then rerank to top_k=5
- [x] LangSmith integration — `@traceable` on retrieve/rerank/chat; prompt version (SHA-256 of prompt files); chunk IDs in trace metadata; litellm LangSmith callback for LLM spans; toggled via `LANGCHAIN_TRACING_V2`
- [ ] Expand golden dataset to 30 questions across GDPR, NIS2, DORA
- [ ] RAGAS evaluation comparison: Phase 1 baseline vs hybrid retrieval

### Phase 3 — Agentic + Analytics (target: 1-2 weeks)
**Goal:** LangGraph router that decides between RAG and quantitative analytics; charts over enforcement data.  
**Exit criterion:** Agent correctly routes RAG vs analytics queries; time-series charts render end-to-end.

- [ ] LangGraph agent with router node (`agent/graph.py`, `agent/router.py`)
- [ ] `search_regulations` tool wrapping the RAG pipeline
- [ ] GDPR fines dataset loaded to S3 as Parquet
- [ ] Athena workgroup + database (Terraform `modules/athena`)
- [ ] `query_metrics` tool (Athena SQL)
- [ ] `generate_chart` tool (matplotlib/plotly → base64)
- [ ] Agent memory/state for multi-turn conversation
- [ ] Prompt injection defense patterns
- [ ] Agent regression test suite

### Phase 4 — Production Hardening (target: 1 week)
**Goal:** Deployable to AWS with full observability, CI/CD, and audit trail.  
**Exit criterion:** CI green on every PR; one-command deploy to AWS; CloudWatch dashboard live.

- [ ] FastAPI hardening: API key auth, rate limiting, structured logging, error handling
- [ ] Audit logging — every query logged with user, timestamp, retrieved chunks, model version, response
- [ ] AWS Lambda + API Gateway deployment (Terraform `modules/lambda`)
- [ ] CloudWatch dashboard: latency, cost per query, error rate
- [ ] GitHub Actions CI: tests + RAGAS eval on PR; Terraform plan on infra PR
- [ ] Architecture diagram (Mermaid) in `docs/diagrams/`
- [ ] ADRs complete (`docs/adr/`)

---

## 7. Architecture Decision Records (ADRs)

### ADR-001 — Vector Store: pgvector over managed vector databases
**Decision:** pgvector on RDS PostgreSQL as primary vector store.  
**Rationale:** Production-grade, no vendor lock-in, native hybrid retrieval via pg_trgm, familiar SQL operations for analytics team integration, lower operational cost than Pinecone/Weaviate at PoC scale.  
**Trade-off:** Less turnkey than managed vector DBs; requires RDS management. Acceptable given Terraform IaC.

### ADR-002 — LLM Provider: AWS Bedrock
**Decision:** AWS Bedrock with Claude 3 Haiku (default) / Sonnet (complex queries).  
**Rationale:** AWS-native, no GPU management, pay-per-token, enterprise security posture (VPC, IAM, no data retention). Consistent with AWS-first architecture.  
**Trade-off:** Bedrock requires explicit model access activation per region. Mitigated by LiteLLM abstraction — trivial to switch to OpenAI or Azure OpenAI if needed.

### ADR-003 — Hybrid Retrieval: semantic + BM25 + re-ranking
**Decision:** Combine pgvector semantic search with pg_trgm keyword search, then re-rank with a cross-encoder.  
**Rationale:** Regulatory text has both semantic content (concepts, obligations) and exact terminology (article numbers, defined terms). Pure semantic retrieval misses exact references; pure BM25 misses conceptual queries. Re-ranking improves precision.  
**Trade-off:** Higher latency than single-stage retrieval. Acceptable for compliance use case where precision > speed.

### ADR-004 — Agent Framework: LangGraph
**Decision:** LangGraph for agent orchestration.  
**Rationale:** Explicit graph-based control flow is essential for a router that decides between RAG and analytics paths. LangGraph provides stateful, inspectable, testable agent graphs — critical for regulated environments requiring auditability.  
**Trade-off:** More verbose than simple LangChain chains. The explicitness is a feature, not a bug, in this context.

### ADR-005 — Chunking Strategy: Recursive Character Splitting (Phase 1)
**Decision:** Recursive character splitting (512 tokens, 50-token overlap) for Phase 1.  
**Rationale:** Zero extra dependencies, fast, deterministic. Sufficient to validate the pipeline end-to-end before optimising retrieval quality.  
**Trade-off:** Structure-blind — chunk boundaries may fall mid-obligation, degrading retrieval precision. To be replaced with semantic chunking in Phase 2. See [`docs/adr/005-chunking-strategy.md`](docs/adr/005-chunking-strategy.md) for full details.

---

## 8. Local Development Setup

### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- AWS CLI configured (for Bedrock calls)
- LangSmith account (free tier)

### Quick start

```bash
# Clone and setup
git clone https://github.com/<your-handle>/compliancerag
cd compliancerag
cp .env.example .env  # fill in AWS credentials + LangSmith API key

# Start local infra (Postgres + pgvector)
docker-compose up -d

# Install dependencies
pip install uv
uv sync

# Run ingestion (GDPR only, local Chroma)
make ingest

# Start API
make dev

# Run evaluation baseline
make eval

# Run tests
make test
```

---

## 9. Environment Variables

```bash
# AWS
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# Vector store
VECTOR_STORE=chroma                # chroma | pgvector
DATABASE_URL=postgresql://...      # used when VECTOR_STORE=pgvector

# Analytics
ATHENA_DATABASE=compliancerag
ATHENA_S3_OUTPUT=s3://compliancerag-athena-results/

# LLMOps
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=compliancerag

# API
API_KEY=                           # simple API key auth for PoC
```

---

## 10. Key Design Principles

1. **Evaluation-first** — RAGAS runs on every PR. No retrieval change ships without measured quality delta.
2. **Auditability** — every query is logged with retrieved chunks, model version, prompt version, and response. Regulatory context demands traceability.
3. **Model-agnostic via LiteLLM** — Bedrock today, OpenAI or Azure OpenAI tomorrow. One line change.
4. **IaC everything** — no manual AWS console operations. Reproducible infra via Terraform.
5. **Local-first development** — Chroma + local Postgres via Docker Compose. No AWS required to develop and test the RAG pipeline.
6. **Prompt versioning** — prompts are files, committed to Git, referenced by version in LangSmith traces.

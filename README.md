# ComplianceRAG

An enterprise-grade AI assistant that answers questions about regulatory compliance (GDPR, NIS2, DORA) by combining hybrid RAG over the full normative text — with exact article citations — and quantitative analytics over enforcement data (fines, incidents, trends), orchestrated by a LangGraph agent backed by AWS Bedrock and pgvector.

**Technical Presentation:** [compliancerag.qsanchez.dev](https://qsanchez.github.io/compliancerag/) · **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) · **ADRs:** [docs/adr/](docs/adr/)

---

## How it works

User questions go through a three-leg hybrid retrieval pipeline:

1. **Semantic** — vector cosine search over regulation text (pgvector + Titan Embeddings v2)
2. **Keyword** — trigram similarity over document text (`pg_trgm`)
3. **Metadata** — trigram similarity over article numbers, titles, and regulation names

Results are fused with Reciprocal Rank Fusion (RRF), reranked by Claude Haiku via LiteLLM, and assembled into a cited response with `[Article X, Regulation]` references. Analytical questions (fines, trends) are routed to an Athena query tool instead.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Managed via [uv](https://github.com/astral-sh/uv) |
| Docker + Docker Compose | For local Postgres/pgvector and Chroma |
| [Task](https://taskfile.dev) | `brew install go-task` |
| AWS account + Bedrock access | Only required for cloud deployment; local dev uses Chroma |

---

## Local development (no AWS required)

1. **Install dependencies**
   ```bash
   uv sync
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env — for local dev only DATABASE_URL is required; leave AWS fields blank
   ```

3. **Start local infrastructure** (Postgres/pgvector + Chroma via Docker Compose)
   ```bash
   task infra:up
   ```

4. **Run the ingestion pipeline**
   ```bash
   task ingest
   ```

5. **Start the API**
   ```bash
   task dev        # FastAPI with hot reload on http://localhost:8000
   ```

### Useful commands

```bash
task test           # full test suite
task test:unit      # unit tests only
task test:integration
task lint           # ruff
task typecheck      # mypy
task eval           # RAGAS evaluation against golden dataset
```

---

## Cloud deployment (AWS)

The full stack runs on AWS Lambda (container image) + API Gateway + RDS pgvector + Bedrock, provisioned with Terraform.

1. **Fill in AWS credentials** in `.env` (see `.env.example`)
2. **Deploy infrastructure**
   ```bash
   cd infra
   terraform init
   terraform apply -var-file=environments/prod.tfvars
   ```
3. **Build and push the Lambda image**
   ```bash
   task deploy:build
   task deploy:push
   task deploy:update-lambda
   ```

Terraform outputs the API endpoint, CloudFront URL, and CloudWatch dashboard URL.

---

## Stack

| Layer | Technology |
|---|---|
| LLM | AWS Bedrock Claude Haiku 4.5 via LiteLLM |
| Embeddings | AWS Bedrock Titan Embeddings v2 |
| Vector store (local) | Chroma |
| Vector store (cloud) | pgvector on RDS PostgreSQL |
| Agent orchestration | LangGraph |
| API | FastAPI |
| Analytics | Athena over Parquet on S3 |
| Auth | Amazon Cognito (Hosted UI + JWT) |
| Frontend | Static HTML/CSS/JS on CloudFront + S3 |
| Observability | CloudWatch (dashboards, metric filters, alarms) |
| IaC | Terraform |

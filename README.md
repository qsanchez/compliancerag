# ComplianceRAG

An enterprise-grade AI assistant that answers questions about regulatory compliance (GDPR, NIS2, DORA) by combining hybrid RAG over the full normative text — with exact article citations — and quantitative analytics over enforcement data (fines, incidents, trends), orchestrated by a LangGraph agent backed by AWS Bedrock and pgvector.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full architecture diagram, stack decisions, ADRs, and phased delivery plan.

## Getting started

1. Copy `.env.example` to `.env` and fill in your AWS credentials and LangSmith API key.
2. Start local infrastructure:
   ```bash
   task infra:up
   ```
3. Install dependencies (requires [uv](https://github.com/astral-sh/uv)):
   ```bash
   uv sync
   ```
4. Run the ingestion pipeline:
   ```bash
   task ingest
   ```
5. Start the API:
   ```bash
   task dev
   ```

Full setup details and environment variable reference are in [ARCHITECTURE.md § 8–9](ARCHITECTURE.md).

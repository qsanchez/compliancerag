# ADR-002 — Embedding Model: Amazon Titan Embeddings v2

**Status:** Accepted — revisit if RAGAS context recall plateaus  
**Date:** 2026-05-08

## Decision

Use **Amazon Titan Embeddings v2** (`amazon.titan-embed-text-v2:0`) via AWS Bedrock for all document and query embeddings.

## Rationale

- **AWS-native** — no additional credentials, IAM policies, or SDK integrations beyond what Bedrock already requires for generation. One less external dependency to manage.
- **1536-dimension vectors** — higher dimensionality than Titan v1 (1024), providing better semantic resolution for long, dense regulatory text.
- **Multilingual support** — handles EU regulatory documents which reference legal Latin terms and cross-language citations.
- **Data residency** — embeddings are computed within AWS; no document content leaves the AWS boundary. Relevant for compliance-sensitive deployments.
- **Cost** — per-token pricing within Bedrock; no separate API key or billing relationship.

## Trade-off

Titan Embeddings v2 is not the highest-performing embedding model available. On standard retrieval benchmarks (MTEB), **Cohere Embed v3** and **OpenAI text-embedding-3-large** outperform it. The choice is AWS consistency and data residency, not raw embedding quality.

## Upgrade Path

If RAGAS context recall stalls and hybrid retrieval + re-ranking does not compensate, evaluate Cohere Embed v3 (also available on Bedrock) as a drop-in replacement — same API surface, no AWS boundary change, measurably stronger on retrieval benchmarks. Measure via RAGAS comparison before merging.

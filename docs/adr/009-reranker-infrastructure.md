# ADR-009 — Reranker Infrastructure: managed API over local inference

**Status:** Accepted  
**Date:** 2026-05-15

## Decision

Replace the locally-executed `cross-encoder/ms-marco-MiniLM-L-6-v2` reranker with
**Cohere Rerank v3.5 via Amazon Bedrock** (`cohere.rerank-v3-5:0`), invoked as a
managed API call from the Lambda function.

As an interim measure during the eu-west-1 → us-east-1 migration (Cohere Rerank is
not available in eu-west-1), the reranker is disabled and the RRF metadata leg
(ADR-003) absorbs most of the precision loss.

## Context

The local cross-encoder was introduced in ADR-003 as the final stage of the hybrid
retrieval pipeline. In production, Lambda cold starts exposed a critical incompatibility:

1. **PyTorch JIT warm-up** on the first forward pass takes 30–60 seconds on CPU. Every
   Lambda cold start re-triggers this, consistently hitting the 60-second function timeout.
2. **ARM64 CPU throughput** — Lambda runs on Graviton2. PyTorch's CPU kernels for ARM64
   lack the AVX-512 vectorisation available on x86, making each transformer forward pass
   slower even after warm-up.
3. **Architecture mismatch** — a cross-encoder requires one full forward pass per
   (query, document) pair. At `fetch_k = 15` candidates, that is 15 sequential inference
   calls on a cold CPU — fundamentally incompatible with a stateless 60-second function.

Increasing the Lambda timeout or adding Provisioned Concurrency eliminates cold starts
but does not fix the per-inference latency; the reranker would still time out on warm
instances with large candidate sets.

## Decision Rationale

Cohere Rerank v3.5 is architecturally a cross-encoder: it jointly processes each
(query, document) pair through a large proprietary transformer and returns relevance
scores — the same algorithmic approach as `ms-marco-MiniLM-L-6-v2`, but with:

- **Inference offloaded to Cohere/AWS GPU infrastructure** — the Lambda function sends
  an HTTP request and receives ranked scores; no local model, no PyTorch, no JIT.
- **Higher model quality** — Cohere Rerank v3.5 is trained on significantly more data
  and with more parameters than MiniLM-L6, improving precision at the top-k positions.
- **No cold start penalty** — API latency is ~100–200 ms regardless of Lambda warm state.
- **Zero infra overhead** — the existing `bedrock-runtime` VPC Interface Endpoint covers
  the call; no NAT Gateway or additional networking required (in us-east-1).
- **IAM-controlled** — `bedrock:Rerank` added to the Lambda execution role; no external
  API keys.

## Trade-offs

| Concern | Impact |
|---|---|
| Per-call cost | $2 / 1000 searches — negligible at PoC traffic |
| us-east-1 dependency | Cohere Rerank is not available in eu-west-1; solution requires us-east-1 deployment |
| External API latency | ~100–200 ms round trip vs. ~0 ms for a warm local model; acceptable given the 60 s timeout problem it replaces |
| Vendor coupling | Cohere Rerank can be swapped for any other reranking API by changing one function; the reranker interface is isolated in `rag/reranker.py` |

## Lessons Learned

Serverless functions are a poor fit for any workload that requires framework
initialisation (PyTorch JIT, model loading) on every cold start. The right boundary is:

- **Lambda**: stateless request handling, LLM API calls, SQL queries, lightweight compute.
- **Managed APIs (Bedrock)**: GPU-backed inference — embeddings, generation, reranking.
- **Persistent compute (ECS/EC2)**: models that must stay resident in memory between requests.

Recognising this boundary and replacing local inference with a managed API is the
architecturally correct decision for a serverless deployment, not a compromise.

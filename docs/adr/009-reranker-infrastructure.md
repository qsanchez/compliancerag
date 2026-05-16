# ADR-009 — Reranker Infrastructure: managed API over local inference

**Status:** Superseded (see Amendment below)  
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

---

## Amendment — 2026-05-16: Cohere Rerank replaced by LLM reranking

**Status:** Accepted

### What changed

The `bedrock-agent-runtime` Cohere Rerank v3.5 integration was abandoned in favour of
**LLM-based reranking using the existing Claude model** (same model as generation, via
LiteLLM). The reranker sends all candidate chunks in a single prompt and asks the model
to return a ranked list of indices.

Each passage is presented with its metadata header:

```
[0] [NIS2 · Art.21 · Security of network systems]
    Cloud providers shall adopt measures proportionate to the risk...

[1] [GDPR · Art.5 · Principles relating to processing]
    Personal data shall be processed lawfully...
```

The model returns a JSON array of indices (`[0, 2, 1, ...]`); the reranker selects the
first `top_k`. On any failure the implementation falls back to vector-similarity order.

### Why Cohere Rerank was abandoned

After the eu-west-1 → us-east-1 migration specifically to access Cohere Rerank:

1. **AWS Marketplace subscription wall** — `bedrock-agent-runtime.rerank()` raises a
   `ValidationException` (HTTP 403) with the message *"not authorized to perform the
   required AWS Marketplace actions (aws-marketplace:ViewSubscriptions,
   aws-marketplace:Subscribe)"*, regardless of IAM policy content.
2. **No self-service activation path** — the Bedrock Model Access page that previously
   handled subscriptions was retired. The replacement flow ("invoke once with a
   Marketplace-permissioned user") also returned the same 403. The Bedrock playground
   for Rerank models is disabled (no generative interface). The AWS Marketplace product
   listing for Cohere Rerank v3.5 prices the model as a **dedicated SageMaker endpoint
   at $3.50/host/hour** — an entirely different product, not the serverless Bedrock API.
3. **No alternative reranking model in Bedrock** — `cohere.rerank-v3-5:0` is the only
   model returned by `list-foundation-models` for the rerank capability in us-east-1.
   Amazon does not offer a native reranking model in the same API.

The Marketplace subscription requirement for serverless Bedrock reranking could not be
completed through any available API, CLI, or console path.

### Decision rationale

Using the existing LLM call for reranking avoids all external dependencies beyond what
is already required for generation:

- **Zero new AWS resources or permissions** — same IAM role, same VPC endpoint, same
  LiteLLM call pattern.
- **Metadata-aware ranking** — the prompt includes `regulation · article · title` for
  each candidate, giving the model stronger relevance signals than text alone.
- **Graceful degradation** — any exception (LLM timeout, malformed JSON) falls back to
  vector-similarity order; the pipeline never hard-fails on the reranker.
- **One API call** — all candidates are ranked in a single completion request (unlike
  a cross-encoder, which requires N calls).

### Trade-offs vs Cohere Rerank

| Concern | Impact |
|---|---|
| Ranking quality | Generative models are less specialised than dedicated cross-encoders; precision at top-1 may be marginally lower |
| Latency | ~300–600 ms extra per query (one additional LLM call) vs ~100–200 ms for Cohere |
| Cost | ~$0.001 per query with Claude Haiku; comparable to Cohere at PoC traffic |
| Token usage | Sending all candidate texts in the prompt consumes input tokens; mitigated by the small candidate set (≤15 chunks) |

### Files changed

| File | Change |
|---|---|
| `rag/reranker.py` | Full rewrite — boto3/Cohere removed, LiteLLM completion added |
| `rag/prompts/rerank.txt` | New prompt file for ranking instruction |
| `config.py` | `reranker_model` field removed |
| `infra/modules/lambda/main.tf` | `RERANKER_MODEL` env var and Marketplace IAM statement removed |

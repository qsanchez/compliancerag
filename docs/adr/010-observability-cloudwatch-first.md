# ADR-010 — Observability: CloudWatch-first over LangSmith

**Status:** Accepted  
**Date:** 2026-05-17

## Decision

Replace LangSmith with a CloudWatch-based observability stack:

1. **Structured logs** — enrich existing `logger.info("chat_request", ...)` with per-span timings (`retrieve_ms`, `rerank_ms`, `generate_ms`), token counts (`input_tokens`, `output_tokens`), and token-based cost (`cost_usd`) extracted from the LiteLLM response usage object.
2. **CloudWatch metric filters** — extract `InputTokens`, `OutputTokens`, `CostUsd`, `RetrieveMs`, `RerankMs`, `GenerateMs`, `InjectionBlocked`, `NoAnswer` from the JSON log stream into custom metrics.
3. **Updated dashboard** — replace the Duration × memory cost proxy with token-based cost; add per-span latency and token count widgets.
4. **Online LLM-as-judge evaluator** — sample 10% of production queries asynchronously (FastAPI `BackgroundTask`); run RAGAS faithfulness + answer_relevancy against the live answer and retrieved context; write scores to `ComplianceRAG/prod` CloudWatch namespace via `boto3.put_metric_data`. Alert if 1-hour rolling faithfulness drops below 0.80.
5. **Remove LangSmith** — drop `langsmith` dependency, `@traceable` decorators, and all `LANGSMITH_*` / `LANGCHAIN_TRACING_V2` environment variables.

## Rationale

The Lambda function runs in a private subnet with no NAT gateway. It cannot establish outbound connections to `api.smith.langchain.com` — traces are silently dropped. Adding a NAT gateway costs ~$32/month plus data-transfer charges, which is not justified for a PoC solely to recover a tracing UI.

CloudWatch is already integrated at zero marginal infrastructure cost:
- Structured JSON logs are already emitted per request.
- Metric filters can extract any numeric field from those logs at negligible cost.
- The CloudWatch dashboard is already deployed via Terraform.

LangSmith's two distinct value propositions need separate replacements:

| LangSmith feature | CloudWatch replacement |
|---|---|
| Per-span operational metrics (latency, tokens, cost) | Enriched structured log fields + metric filters |
| LLM quality monitoring on real traffic | Online LLM-as-judge evaluator (RAGAS) |

The offline RAGAS evaluator (30 fixed questions) catches regressions from code changes but does not cover quality drift on real user traffic. The online evaluator samples production queries, so it detects issues caused by query distribution shift, stale regulation data, or model behaviour changes — none of which the offline golden dataset would surface.

## Trade-off

LangSmith provides a waterfall trace UI that shows the full call tree (retrieve → rerank → generate) with inputs and outputs at each node. This is the one capability CloudWatch logs cannot replicate without a structured trace viewer.

Mitigations:
- Per-span timing fields in every log line allow Log Insights queries to reconstruct the breakdown per request.
- The online RAGAS widget provides continuous quality signal on real traffic.
- If a NAT gateway is added in the future for any other reason (e.g. third-party API access), LangSmith can be re-enabled with a single env var change (`LANGCHAIN_TRACING_V2=true`) — the `@traceable` decorators will be gone, but re-adding them is a small effort.

## Consequences

- `langsmith` removed from `pyproject.toml`; CI no longer needs `LANGCHAIN_TRACING_V2=false`
- `ONLINE_EVAL_SAMPLE_RATE` new env var (default `0.1`) — set to `0` to disable online evaluation
- Online evaluation adds one LLM call per sampled request (~500 ms, ~800 tokens) in a background task; does not affect response latency
- CloudWatch custom metric costs: ~$0.30/month per metric (10 new metrics ≈ $3/month)

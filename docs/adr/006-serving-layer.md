# ADR-006 — Serving Layer: Lambda for PoC, Fargate deferred to production

**Status:** Accepted — revisit in Phase 4  
**Date:** 2026-05-08

## Decision

Phase 1–3 serve the FastAPI application via **AWS Lambda + API Gateway**.  
ECS Fargate is deferred to Phase 4 (Production Hardening).

## Rationale

- Lambda requires zero cluster management and has no idle cost — correct for a PoC with unpredictable, low traffic.
- API Gateway + Lambda is fully expressible in Terraform with minimal configuration.
- FastAPI runs on Lambda without code changes (ASGI adapter handles the event translation).
- Keeps infrastructure complexity low while the RAG pipeline and agent are being built and evaluated.

## Limitation

Lambda has constraints that matter at production scale:

- **Cold starts** — first invocation after idle spins up a new container; acceptable for PoC, problematic for SLA-bound production traffic.
- **15-minute execution limit** — not a concern for synchronous chat responses, but relevant if long-running analytics queries are added.
- **Concurrency model** — scaling is per-request rather than per-container; cost profile diverges from Fargate at sustained high throughput.

## Upgrade Path

Migrate to **ECS Fargate + Application Load Balancer** in Phase 4:

- Replace the Lambda Terraform module (`infra/modules/lambda`) with an ECS module.
- Add an ALB in the public subnet; ECS tasks run in the private subnet.
- No FastAPI code changes required — the same container image runs locally, on Lambda, and on Fargate.
- Measure cold-start impact before migrating; if acceptable, Lambda can remain indefinitely.

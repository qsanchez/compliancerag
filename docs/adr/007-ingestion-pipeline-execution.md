# ADR-007 — Ingestion Pipeline Execution: Local for PoC, GitHub Actions deferred

**Status:** Accepted — revisit in Phase 4  
**Date:** 2026-05-08

## Decision

The ingestion pipeline (`task ingest`) runs **locally from the developer's machine** for the PoC.  
GitHub Actions and AWS-hosted execution are deferred to Phase 4.

## Rationale

- **EUR-Lex blocks AWS IPs** — NIS2 and DORA source documents are fetched from EUR-Lex, which blocks programmatic access from AWS via WAF. Ingestion must run outside AWS regardless.
- **RDS is in a private subnet** — GitHub Actions runners are outside the VPC and cannot reach RDS directly. Bridging this requires a public RDS endpoint (bad practice) or additional infrastructure (VPN, bastion, or a loading Lambda).
- **Regulatory text changes rarely** — GDPR, NIS2, and DORA are stable documents. There is no requirement for automated or scheduled re-ingestion at PoC stage.
- **Enforcement data is static** — the CSV datasets (GDPR fines, ENISA reports) are loaded once and updated manually. No scheduling benefit.
- **Keeps infrastructure minimal** — no extra AWS components, no IAM role for CI, no S3-to-RDS loading Lambda needed during PoC phases.

## Why GitHub Actions was considered but rejected for now

GitHub Actions is free for public repositories (unlimited minutes), but introduces two problems:

1. **AWS credentials in a public repo** — even with encrypted secrets and OIDC, the attack surface of a public repo is wider than a private one. A least-privilege IAM role mitigates but does not eliminate the risk.
2. **RDS connectivity** — the private subnet placement of RDS is the hard blocker. Resolving it requires architectural changes not justified at PoC scale.

## Upgrade Path

In Phase 4, evaluate one of the following:

- **GitHub Actions + S3 staging** — ingestion writes embedded chunks to S3; a Lambda inside the VPC loads them into RDS. Keeps EUR-Lex fetching outside AWS.
- **AWS Batch / ECS Task** — a containerised ingestion job triggered manually or via EventBridge, running inside the VPC with direct RDS access. Requires pre-fetching source documents to S3 (since EUR-Lex blocks AWS IPs).

Move to a private repository before implementing either option with live AWS credentials.

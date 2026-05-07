# ADR-005 — Chunking Strategy: Recursive Character Splitting (Phase 1)

**Status:** Accepted — revisit in Phase 2  
**Date:** 2026-05-07

## Decision

Phase 1 uses **recursive character splitting** (split on `\n\n`, then `\n`, then `.`, then space) with a fixed token budget of 512 tokens and 50-token overlap, implemented in `ingestion/chunker.py` using tiktoken.

## Rationale

- Zero additional dependencies or model calls — purely text-based, fast, deterministic.
- Good enough for Phase 1's exit criterion (RAGAS faithfulness ≥ 0.7 on 10 GDPR questions).
- Regulatory articles tend to have natural paragraph breaks that align with the separator hierarchy, so recursive splitting produces reasonably coherent chunks in practice.
- Keeps ingestion cost and latency low while the pipeline is being validated end-to-end.

## Limitation

Recursive character splitting is **structure-blind**: it does not understand that a 600-token article is a single coherent unit, or that a list of obligations across three paragraphs should stay together. A chunk boundary may fall in the middle of a legal obligation, splitting the condition from its consequence. This degrades retrieval precision — the retrieved chunk may contain only half the relevant rule, leading to incomplete or misleading answers.

## Alternative: Semantic Chunking

Semantic chunking embeds each sentence (or paragraph) and splits only when the cosine similarity between adjacent sentences drops below a threshold, keeping topically coherent passages together. This produces chunks that are semantically meaningful rather than arbitrarily token-bounded.

**Trade-off:** Requires an embedding call per sentence during ingestion (higher cost, higher latency). For the GDPR corpus (~500K tokens) this is acceptable but adds complexity before the basic pipeline is validated.

## Upgrade Path

Replace `ingestion/chunker.py` with a semantic chunker in Phase 2, alongside the move to pgvector. Measure the impact via RAGAS comparison against the Phase 1 baseline before merging.

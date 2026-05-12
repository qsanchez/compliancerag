# ADR-004 — Agent Framework: LangGraph

**Status:** Accepted  
**Date:** 2026-05-08

## Decision

Use **LangGraph** (`langgraph`) for agent orchestration. The agent is a `StateGraph` with three nodes — `router`, `rag`, `analytics` — and a conditional edge from `router` that dispatches to `rag` or `analytics` based on query classification. Graph state is typed via a `TypedDict` (`AgentState`).

## Rationale

- **Explicit control flow** — the routing decision (RAG vs. analytics) is a hard branch, not an LLM-inferred chain of thought. `StateGraph` expresses this as a first-class conditional edge, making the dispatch logic inspectable and testable without running the LLM.
- **Auditability** — in regulated environments, every decision point must be traceable. LangGraph's graph structure means the execution path (which node ran, in what order) is part of the observable state, not buried in an opaque agent loop.
- **Determinism** — unlike ReAct-style agents that loop until the model decides to stop, this graph has a fixed depth of 2 (router → terminal node). There is no risk of runaway tool-calling or unbounded execution cost.
- **Testability** — each node is a plain Python function that takes and returns `AgentState`. Unit tests can call nodes directly without spinning up the full graph.
- **Existing expertise** — familiarity with LangGraph reduces implementation risk compared to adopting an unfamiliar framework (Autogen, CrewAI) for the same purpose.

## Trade-off

LangGraph is more verbose than a simple `if/else` router or a single LangChain `ConversationChain`. For the current two-branch routing problem, the graph machinery is heavier than strictly necessary. The verbosity pays off if the agent gains additional nodes (e.g., a clarification node, a citation-validation node, or multi-step analytics planning), which the graph structure accommodates without restructuring.

## Alternatives Considered

- **Plain `if/else` router** — simpler, but couples routing logic to the API handler and makes it harder to add nodes later without refactoring.
- **LangChain AgentExecutor / ReAct** — loop-based; unpredictable depth; harder to audit execution path; overkill for two deterministic branches.
- **CrewAI / Autogen** — multi-agent frameworks designed for collaborative agent teams; far heavier than needed for a single-router, two-branch dispatch.

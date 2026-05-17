import time
from pathlib import Path
from typing import TypedDict

import litellm
import structlog

from config import get_settings
from rag import context_builder, reranker, retriever
from rag.retriever import RetrievedChunk, _detect_regulations

_TOP_K = 5
_TOP_K_PER_REG = 4  # chunks per regulation for cross-regulation comparison queries
_TOP_K_NO_RERANKER = 10  # fetch more when reranker is off to compensate for lower precision
_PROMPTS_DIR = Path(__file__).parent / "prompts"

logger = structlog.get_logger()


class PipelineResult(TypedDict):
    answer: str
    citations: list[str]
    chunks: list[RetrievedChunk]
    retrieve_ms: float
    rerank_ms: float
    generate_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float


def _enforce_balance(
    ranked: list[RetrievedChunk],
    regulations: list[str],
    top_k: int,
) -> list[RetrievedChunk]:
    """Pick top_k chunks from a fully-ranked list ensuring each regulation
    gets at least floor(top_k/n) slots, then fills remaining slots in rank order.
    """
    min_per_reg = top_k // len(regulations)
    quota: dict[str, int] = {reg: min_per_reg for reg in regulations}

    result: list[RetrievedChunk] = []
    deferred: list[RetrievedChunk] = []

    for chunk in ranked:
        reg = chunk["metadata"].get("regulation", "").upper()
        if reg in quota and quota[reg] > 0:
            result.append(chunk)
            quota[reg] -= 1
        else:
            deferred.append(chunk)

    for chunk in deferred:
        if len(result) >= top_k:
            break
        result.append(chunk)

    return result[:top_k]


def run(query: str, history: list[dict] | None = None) -> PipelineResult:
    settings = get_settings()
    regulations = _detect_regulations(query)
    top_k = _TOP_K_PER_REG * len(regulations) if len(regulations) > 1 else _TOP_K
    fetch_k = top_k * reranker.FETCH_MULTIPLIER if settings.reranker_enabled else _TOP_K_NO_RERANKER

    t0 = time.perf_counter()
    pool = retriever.retrieve(query, top_k=fetch_k)
    retrieve_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    if settings.reranker_enabled:
        if len(regulations) > 1:
            all_ranked = reranker.rerank(query, pool, top_k=len(pool))
            chunks = _enforce_balance(all_ranked, regulations, _TOP_K_PER_REG * len(regulations))
        else:
            chunks = reranker.rerank(query, pool, top_k=_TOP_K)
    else:
        chunks = pool[:_TOP_K_NO_RERANKER]
    rerank_ms = (time.perf_counter() - t0) * 1000

    ctx = context_builder.build(chunks)

    system_prompt = (_PROMPTS_DIR / "rag_system.txt").read_text()
    user_prompt = (
        (_PROMPTS_DIR / "rag_user.txt")
        .read_text()
        .format(
            context=ctx["context"],
            question=query,
        )
    )
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *(history or []),
        {"role": "user", "content": user_prompt},
    ]

    t0 = time.perf_counter()
    response = litellm.completion(model=settings.litellm_model, messages=messages)
    generate_ms = (time.perf_counter() - t0) * 1000

    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    try:
        cost_usd = litellm.completion_cost(completion_response=response)
    except Exception:
        cost_usd = 0.0

    logger.info(
        "pipeline_spans",
        retrieve_ms=round(retrieve_ms, 1),
        rerank_ms=round(rerank_ms, 1),
        generate_ms=round(generate_ms, 1),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost_usd, 6),
    )

    return PipelineResult(
        answer=response.choices[0].message.content or "",
        citations=ctx["citations"],
        chunks=chunks,
        retrieve_ms=retrieve_ms,
        rerank_ms=rerank_ms,
        generate_ms=generate_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )

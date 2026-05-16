from pathlib import Path
from typing import TypedDict

import litellm
from langsmith import traceable

from config import get_settings
from rag import context_builder, reranker, retriever
from rag.retriever import RetrievedChunk, _detect_regulations

_TOP_K = 5
_TOP_K_PER_REG = 4  # chunks per regulation for cross-regulation comparison queries
_TOP_K_NO_RERANKER = 10  # fetch more when reranker is off to compensate for lower precision
_PROMPTS_DIR = Path(__file__).parent / "prompts"


class PipelineResult(TypedDict):
    answer: str
    citations: list[str]
    chunks: list[RetrievedChunk]


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


@traceable(name="search_regulations", run_type="tool")
def run(query: str, history: list[dict] | None = None) -> PipelineResult:
    settings = get_settings()
    regulations = _detect_regulations(query)
    top_k = _TOP_K_PER_REG * len(regulations) if len(regulations) > 1 else _TOP_K
    fetch_k = top_k * reranker.FETCH_MULTIPLIER if settings.reranker_enabled else _TOP_K_NO_RERANKER
    pool = retriever.retrieve(query, top_k=fetch_k)

    if settings.reranker_enabled:
        if len(regulations) > 1:
            all_ranked = reranker.rerank(query, pool, top_k=len(pool))
            chunks = _enforce_balance(all_ranked, regulations, _TOP_K_PER_REG * len(regulations))
        else:
            chunks = reranker.rerank(query, pool, top_k=_TOP_K)
    else:
        chunks = pool[:_TOP_K_NO_RERANKER]

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
    response = litellm.completion(model=settings.litellm_model, messages=messages)

    return PipelineResult(
        answer=response.choices[0].message.content or "",
        citations=ctx["citations"],
        chunks=chunks,
    )

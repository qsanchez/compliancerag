from pathlib import Path
from typing import TypedDict

import litellm
from langsmith import traceable

from config import get_settings
from rag import context_builder, reranker, retriever
from rag.retriever import RetrievedChunk

_TOP_K = 5
_TOP_K_NO_RERANKER = 10  # fetch more when reranker is off to compensate for lower precision
_PROMPTS_DIR = Path(__file__).parent / "prompts"


class PipelineResult(TypedDict):
    answer: str
    citations: list[str]
    chunks: list[RetrievedChunk]


@traceable(name="search_regulations", run_type="tool")
def run(query: str, history: list[dict] | None = None) -> PipelineResult:
    settings = get_settings()
    fetch_k = _TOP_K * reranker.FETCH_MULTIPLIER if settings.reranker_enabled else _TOP_K_NO_RERANKER
    chunks = retriever.retrieve(query, top_k=fetch_k)
    if settings.reranker_enabled:
        chunks = reranker.rerank(query, chunks, top_k=_TOP_K)
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

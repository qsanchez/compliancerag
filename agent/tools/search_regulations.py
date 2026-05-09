from pathlib import Path

import litellm
from langsmith import traceable

from config import get_settings
from rag import context_builder, reranker, retriever

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "rag" / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


@traceable(name="search_regulations", run_type="tool")
def search_regulations(question: str, history: list[dict] | None = None) -> dict:
    settings = get_settings()
    fetch_k = 5 * reranker.FETCH_MULTIPLIER if settings.reranker_enabled else 5
    chunks = retriever.retrieve(question, top_k=fetch_k)
    if settings.reranker_enabled:
        chunks = reranker.rerank(question, chunks, top_k=5)

    ctx = context_builder.build(chunks)
    system_prompt = _load_prompt("rag_system.txt")
    user_prompt = _load_prompt("rag_user.txt").format(
        context=ctx["context"],
        question=question,
    )

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *(history or []),
        {"role": "user", "content": user_prompt},
    ]

    response = litellm.completion(model=settings.litellm_model, messages=messages)
    return {
        "answer": response.choices[0].message.content or "",
        "citations": ctx["citations"],
    }

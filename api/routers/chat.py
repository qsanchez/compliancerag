from pathlib import Path

import litellm
import structlog
from fastapi import APIRouter, HTTPException

from api.models import ChatRequest, ChatResponse
from config import get_settings
from rag import context_builder, reranker, retriever

logger = structlog.get_logger()

router = APIRouter()

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "rag" / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    fetch_k = 5 * reranker.FETCH_MULTIPLIER if settings.reranker_enabled else 5
    chunks = retriever.retrieve(request.question, top_k=fetch_k)
    if settings.reranker_enabled:
        chunks = reranker.rerank(request.question, chunks, top_k=5)
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant regulatory text found for this question.",
        )

    ctx = context_builder.build(chunks)
    system_prompt = _load_prompt("rag_system.txt")
    user_prompt = _load_prompt("rag_user.txt").format(
        context=ctx["context"],
        question=request.question,
    )

    logger.info(
        "chat_request",
        question=request.question,
        chunk_ids=[c["metadata"].get("source_id", "") for c in chunks],
        model=settings.litellm_model,
        system_prompt_file="rag_system.txt",
        user_prompt_file="rag_user.txt",
    )

    response = litellm.completion(
        model=settings.litellm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    answer = response.choices[0].message.content or ""
    return ChatResponse(answer=answer, citations=ctx["citations"])

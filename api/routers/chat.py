import hashlib
from pathlib import Path

import litellm
import structlog
from fastapi import APIRouter, HTTPException
from langsmith import get_current_run_tree, traceable

from api.models import ChatRequest, ChatResponse
from config import get_settings
from rag import context_builder, reranker, retriever

logger = structlog.get_logger()

router = APIRouter()

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "rag" / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _prompt_version() -> str:
    """SHA-256 (truncated) of both prompt files — changes whenever prompts are edited."""
    content = _load_prompt("rag_system.txt") + _load_prompt("rag_user.txt")
    return hashlib.sha256(content.encode()).hexdigest()[:12]


@router.post("/chat", response_model=ChatResponse)
@traceable(name="chat", run_type="chain")
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

    prompt_ver = _prompt_version()
    chunk_ids = [c["metadata"].get("source_id", c["metadata"].get("id", "")) for c in chunks]

    # Enrich the LangSmith trace with prompt version and retrieved chunk IDs
    run = get_current_run_tree()
    if run:
        run.metadata.update({"prompt_version": prompt_ver, "chunk_ids": chunk_ids, "model": settings.litellm_model})

    logger.info(
        "chat_request",
        question=request.question,
        chunk_ids=chunk_ids,
        model=settings.litellm_model,
        prompt_version=prompt_ver,
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

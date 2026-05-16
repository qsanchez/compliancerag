from __future__ import annotations

import json
import logging
from pathlib import Path

import litellm
from langsmith import traceable

from config import get_settings
from rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

FETCH_MULTIPLIER = 3

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _format_source(index: int, chunk: RetrievedChunk) -> str:
    m = chunk["metadata"]
    regulation = m.get("regulation", "").upper()
    article = m.get("article_number", "")
    title = m.get("title", "")
    label = " · ".join(filter(None, [regulation, f"Art.{article}" if article else "", title]))
    return f"[{index}] [{label}]\n{chunk['text']}"


@traceable(name="rerank", run_type="chain")
def rerank(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    if not chunks:
        return chunks

    settings = get_settings()
    system_prompt = (_PROMPTS_DIR / "rerank.txt").read_text()
    sources_text = "\n\n".join(_format_source(i, c) for i, c in enumerate(chunks))
    user_message = f"Query: {query}\n\nPassages:\n{sources_text}"

    try:
        response = litellm.completion(
            model=settings.litellm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=256,
            temperature=0,
        )
        raw = response.choices[0].message.content or ""
        ranked_indices: list[int] = json.loads(raw.strip())
    except Exception as exc:
        logger.warning("Reranker failed, using vector similarity order: %s", exc)
        return chunks[:top_k]

    seen: set[int] = set()
    result: list[RetrievedChunk] = []
    for idx in ranked_indices:
        if isinstance(idx, int) and 0 <= idx < len(chunks) and idx not in seen:
            result.append(chunks[idx])
            seen.add(idx)
            if len(result) == top_k:
                break

    # Safety: if parsing returned fewer than top_k, pad with remaining chunks
    if len(result) < top_k:
        for i, chunk in enumerate(chunks):
            if i not in seen:
                result.append(chunk)
                if len(result) == top_k:
                    break

    return result

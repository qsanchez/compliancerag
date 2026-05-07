from langsmith import traceable
from sentence_transformers import CrossEncoder

from config import get_settings
from rag.retriever import RetrievedChunk

_model: CrossEncoder | None = None

# Candidates multiplier: fetch this many chunks from the retriever before reranking.
FETCH_MULTIPLIER = 3


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(get_settings().reranker_model)
    return _model


@traceable(name="rerank", run_type="chain")
def rerank(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    if not chunks:
        return chunks
    model = _get_model()
    pairs = [(query, chunk["text"]) for chunk in chunks]
    scores: list[float] = model.predict(pairs).tolist()
    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [RetrievedChunk(text=c["text"], metadata=c["metadata"], score=s) for s, c in ranked[:top_k]]

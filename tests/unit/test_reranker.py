from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from rag.reranker import FETCH_MULTIPLIER, rerank
from rag.retriever import RetrievedChunk


def _make_chunks(n: int) -> list[RetrievedChunk]:
    return [RetrievedChunk(text=f"chunk {i}", metadata={"id": str(i)}, score=0.5) for i in range(n)]


@pytest.fixture(autouse=True)
def reset_model():
    """Reset the cached cross-encoder between tests."""
    import rag.reranker as mod
    original = mod._model
    mod._model = None
    yield
    mod._model = original


def test_rerank_returns_top_k():
    mock_model = MagicMock()
    # Assign scores in reverse order so chunk n-1 ranks first
    chunks = _make_chunks(6)
    mock_model.predict.return_value = np.array([float(i) for i in range(6)])

    with patch("rag.reranker._get_model", return_value=mock_model):
        result = rerank("query", chunks, top_k=3)

    assert len(result) == 3
    # Highest scores (5, 4, 3) → chunks 5, 4, 3
    assert result[0]["text"] == "chunk 5"
    assert result[1]["text"] == "chunk 4"
    assert result[2]["text"] == "chunk 3"


def test_rerank_score_updated():
    mock_model = MagicMock()
    chunks = _make_chunks(2)
    mock_model.predict.return_value = np.array([0.9, 0.1])

    with patch("rag.reranker._get_model", return_value=mock_model):
        result = rerank("query", chunks, top_k=2)

    assert result[0]["score"] == pytest.approx(0.9)
    assert result[1]["score"] == pytest.approx(0.1)


def test_rerank_calls_model_with_pairs():
    mock_model = MagicMock()
    chunks = _make_chunks(3)
    mock_model.predict.return_value = np.array([0.3, 0.1, 0.2])

    with patch("rag.reranker._get_model", return_value=mock_model):
        rerank("my query", chunks, top_k=3)

    pairs = mock_model.predict.call_args[0][0]
    assert pairs == [("my query", "chunk 0"), ("my query", "chunk 1"), ("my query", "chunk 2")]


def test_rerank_empty_input():
    result = rerank("query", [], top_k=5)
    assert result == []


def test_fetch_multiplier_is_positive_integer():
    assert isinstance(FETCH_MULTIPLIER, int)
    assert FETCH_MULTIPLIER > 1

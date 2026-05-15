from unittest.mock import MagicMock, patch

import pytest

from rag.reranker import FETCH_MULTIPLIER, rerank
from rag.retriever import RetrievedChunk


def _make_chunks(n: int) -> list[RetrievedChunk]:
    return [RetrievedChunk(text=f"chunk {i}", metadata={"id": str(i)}, score=0.5) for i in range(n)]


def _mock_client(results: list[dict]) -> MagicMock:
    client = MagicMock()
    client.rerank.return_value = {"rerankingResults": results}
    return client


def test_rerank_returns_top_k():
    chunks = _make_chunks(6)
    # API returns top_k=3 results ordered by score, referencing original indices
    mock_results = [
        {"index": 5, "relevanceScore": 0.9},
        {"index": 4, "relevanceScore": 0.8},
        {"index": 3, "relevanceScore": 0.7},
    ]
    with patch("boto3.client", return_value=_mock_client(mock_results)):
        result = rerank("query", chunks, top_k=3)

    assert len(result) == 3
    assert result[0]["text"] == "chunk 5"
    assert result[1]["text"] == "chunk 4"
    assert result[2]["text"] == "chunk 3"


def test_rerank_score_updated():
    chunks = _make_chunks(2)
    mock_results = [
        {"index": 0, "relevanceScore": 0.9},
        {"index": 1, "relevanceScore": 0.1},
    ]
    with patch("boto3.client", return_value=_mock_client(mock_results)):
        result = rerank("query", chunks, top_k=2)

    assert result[0]["score"] == pytest.approx(0.9)
    assert result[1]["score"] == pytest.approx(0.1)


def test_rerank_passes_query_and_sources():
    chunks = _make_chunks(3)
    mock_client = _mock_client([{"index": 0, "relevanceScore": 0.5}])

    with patch("boto3.client", return_value=mock_client):
        rerank("my query", chunks, top_k=1)

    call_kwargs = mock_client.rerank.call_args[1]
    assert call_kwargs["queries"][0]["textQuery"]["text"] == "my query"
    sources = call_kwargs["sources"]
    assert len(sources) == 3
    assert sources[0]["inlineDocumentSource"]["textDocument"]["text"] == "chunk 0"


def test_rerank_empty_input():
    result = rerank("query", [], top_k=5)
    assert result == []


def test_fetch_multiplier_is_positive_integer():
    assert isinstance(FETCH_MULTIPLIER, int)
    assert FETCH_MULTIPLIER > 1

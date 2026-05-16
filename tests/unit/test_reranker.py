from unittest.mock import MagicMock, patch

from rag.reranker import FETCH_MULTIPLIER, rerank
from rag.retriever import RetrievedChunk


def _make_chunks(n: int) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            text=f"chunk {i}",
            metadata={
                "regulation": "GDPR",
                "article_number": str(i),
                "title": f"Article {i}",
                "chapter": "1",
            },
            score=0.5,
        )
        for i in range(n)
    ]


def _mock_completion(ranked_indices: list[int]) -> MagicMock:
    import json

    response = MagicMock()
    response.choices[0].message.content = json.dumps(ranked_indices)
    return response


def test_rerank_returns_top_k():
    chunks = _make_chunks(6)
    with patch("litellm.completion", return_value=_mock_completion([5, 4, 3, 0, 1, 2])):
        result = rerank("query", chunks, top_k=3)

    assert len(result) == 3
    assert result[0]["text"] == "chunk 5"
    assert result[1]["text"] == "chunk 4"
    assert result[2]["text"] == "chunk 3"


def test_rerank_uses_all_indices():
    chunks = _make_chunks(4)
    with patch("litellm.completion", return_value=_mock_completion([2, 0, 3, 1])):
        result = rerank("query", chunks, top_k=4)

    assert [r["text"] for r in result] == ["chunk 2", "chunk 0", "chunk 3", "chunk 1"]


def test_rerank_fallback_on_error():
    chunks = _make_chunks(5)
    with patch("litellm.completion", side_effect=Exception("LLM unavailable")):
        result = rerank("query", chunks, top_k=3)

    assert len(result) == 3
    assert result[0]["text"] == "chunk 0"


def test_rerank_empty_input():
    result = rerank("query", [], top_k=5)
    assert result == []


def test_fetch_multiplier_is_positive_integer():
    assert isinstance(FETCH_MULTIPLIER, int)
    assert FETCH_MULTIPLIER > 1

from unittest.mock import MagicMock, patch

import pytest

from rag.retriever import retrieve


def _make_chroma_result(n: int) -> dict:
    docs = [f"regulatory text {i}" for i in range(n)]
    metas = [
        {"article_number": f"Article {i}", "regulation": "GDPR", "source_id": f"gdpr-art-{i}"}
        for i in range(n)
    ]
    distances = [0.1 * i for i in range(n)]
    return {
        "documents": [docs],
        "metadatas": [metas],
        "distances": [distances],
    }


@patch("rag.retriever.indexer.get_collection")
@patch("rag.retriever.embedder.embed")
def test_retrieve_returns_correct_count(
    mock_embed: MagicMock, mock_get_collection: MagicMock
) -> None:
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    collection = MagicMock()
    collection.query.return_value = _make_chroma_result(5)
    mock_get_collection.return_value = collection

    result = retrieve("What is Article 32?", top_k=5)
    assert len(result) == 5


@patch("rag.retriever.indexer.get_collection")
@patch("rag.retriever.embedder.embed")
def test_retrieve_chunk_structure(mock_embed: MagicMock, mock_get_collection: MagicMock) -> None:
    mock_embed.return_value = [[0.5, 0.5]]
    collection = MagicMock()
    collection.query.return_value = _make_chroma_result(3)
    mock_get_collection.return_value = collection

    result = retrieve("data breach notification")
    for chunk in result:
        assert "text" in chunk
        assert "metadata" in chunk
        assert "score" in chunk
        assert isinstance(chunk["score"], float)
        assert 0.0 <= chunk["score"] <= 1.0


@patch("rag.retriever.indexer.get_collection")
@patch("rag.retriever.embedder.embed")
def test_retrieve_embeds_query(mock_embed: MagicMock, mock_get_collection: MagicMock) -> None:
    mock_embed.return_value = [[0.1, 0.2]]
    collection = MagicMock()
    collection.query.return_value = _make_chroma_result(1)
    mock_get_collection.return_value = collection

    query = "What are GDPR fines?"
    retrieve(query)
    mock_embed.assert_called_once_with([query])


@patch("rag.retriever.indexer.get_collection")
@patch("rag.retriever.embedder.embed")
def test_retrieve_score_conversion(mock_embed: MagicMock, mock_get_collection: MagicMock) -> None:
    mock_embed.return_value = [[0.0]]
    collection = MagicMock()
    # distance=0 should give score=1.0, distance=2 should give score=0.0
    collection.query.return_value = {
        "documents": [["text a", "text b"]],
        "metadatas": [
            [
                {"article_number": "Art 1", "regulation": "GDPR", "source_id": "x"},
                {"article_number": "Art 2", "regulation": "GDPR", "source_id": "y"},
            ]
        ],
        "distances": [[0.0, 2.0]],
    }
    mock_get_collection.return_value = collection

    result = retrieve("query")
    assert result[0]["score"] == pytest.approx(1.0)
    assert result[1]["score"] == pytest.approx(0.0)

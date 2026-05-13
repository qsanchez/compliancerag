from unittest.mock import MagicMock, patch

from rag.retriever import retrieve


def _make_rows(n: int) -> list[tuple]:
    return [
        (
            f"gdpr-art-{i}",
            f"regulatory text {i}",
            {"article_number": f"Article {i}", "regulation": "GDPR"},
            0.9 - 0.1 * i,
        )
        for i in range(n)
    ]


def _mock_conn(semantic_rows: list, keyword_rows: list) -> MagicMock:
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchall.side_effect = [semantic_rows, keyword_rows]

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_returns_correct_count(mock_embed: MagicMock, mock_conn: MagicMock) -> None:
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    rows = _make_rows(5)
    mock_conn.return_value = _mock_conn(rows, rows)

    result = retrieve("What is Article 32?", top_k=5)
    assert len(result) == 5


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_chunk_structure(mock_embed: MagicMock, mock_conn: MagicMock) -> None:
    mock_embed.return_value = [[0.5, 0.5]]
    rows = _make_rows(3)
    mock_conn.return_value = _mock_conn(rows, rows)

    result = retrieve("data breach notification")
    for chunk in result:
        assert "text" in chunk
        assert "metadata" in chunk
        assert "score" in chunk
        assert isinstance(chunk["score"], float)


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_embeds_query(mock_embed: MagicMock, mock_conn: MagicMock) -> None:
    mock_embed.return_value = [[0.1, 0.2]]
    rows = _make_rows(1)
    mock_conn.return_value = _mock_conn(rows, rows)

    query = "What are GDPR fines?"
    retrieve(query)
    mock_embed.assert_called_once_with([query])


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_rrf_boosts_overlap(mock_embed: MagicMock, mock_conn: MagicMock) -> None:
    mock_embed.return_value = [[0.0]]
    # doc-0 appears in both semantic and keyword → gets double RRF contribution
    semantic: list[tuple[str, str, dict, float]] = [
        ("doc-0", "text 0", {}, 0.9),
        ("doc-1", "text 1", {}, 0.8),
    ]
    keyword: list[tuple[str, str, dict, float]] = [
        ("doc-0", "text 0", {}, 0.9),
        ("doc-2", "text 2", {}, 0.7),
    ]
    mock_conn.return_value = _mock_conn(semantic, keyword)

    result = retrieve("query", top_k=3)
    assert result[0]["text"] == "text 0"

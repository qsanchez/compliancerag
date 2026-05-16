from unittest.mock import MagicMock, patch

from rag.retriever import _detect_regulations, retrieve


def _make_rows(n: int, regulation: str = "GDPR") -> list[tuple]:
    return [
        (
            f"{regulation.lower()}-art-{i}",
            f"{regulation} regulatory text {i}",
            {
                "article_number": str(i),
                "regulation": regulation,
                "title": f"Article {i}",
                "chapter": "I",
            },
            0.9 - 0.1 * i,
        )
        for i in range(n)
    ]


def _mock_conn(fetchall_returns: list[list]) -> MagicMock:
    """Build a mock connection whose cursor.fetchall() returns successive lists."""
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchall.side_effect = fetchall_returns

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn


# ── _detect_regulations ───────────────────────────────────────────────────────


def test_detect_single_regulation():
    assert _detect_regulations("What does GDPR say about consent?") == ["GDPR"]


def test_detect_multiple_regulations():
    regs = _detect_regulations("differences between GDPR and NIS2")
    assert set(regs) == {"GDPR", "NIS2"}


def test_detect_all_three():
    regs = _detect_regulations("compare GDPR, NIS2 and DORA")
    assert set(regs) == {"GDPR", "NIS2", "DORA"}


def test_detect_no_regulation():
    assert _detect_regulations("What is a data breach?") == []


# ── Single-regulation retrieval ───────────────────────────────────────────────


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_returns_correct_count(mock_embed: MagicMock, mock_conn: MagicMock) -> None:
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    rows = _make_rows(5)
    # 3 legs, each returning the same rows
    mock_conn.return_value = _mock_conn([rows, rows, rows])

    result = retrieve("What is Article 32?", top_k=5)
    assert len(result) == 5


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_chunk_structure(mock_embed: MagicMock, mock_conn: MagicMock) -> None:
    mock_embed.return_value = [[0.5, 0.5]]
    rows = _make_rows(3)
    mock_conn.return_value = _mock_conn([rows, rows, rows])

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
    mock_conn.return_value = _mock_conn([rows, rows, rows])

    query = "What are GDPR fines?"
    retrieve(query)
    mock_embed.assert_called_once_with([query])


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_rrf_boosts_overlap(mock_embed: MagicMock, mock_conn: MagicMock) -> None:
    mock_embed.return_value = [[0.0]]
    semantic: list[tuple] = [("doc-0", "text 0", {}, 0.9), ("doc-1", "text 1", {}, 0.8)]
    keyword: list[tuple] = [("doc-0", "text 0", {}, 0.9), ("doc-2", "text 2", {}, 0.7)]
    metadata: list[tuple] = [("doc-1", "text 1", {}, 0.8)]
    mock_conn.return_value = _mock_conn([semantic, keyword, metadata])

    result = retrieve("query", top_k=3)
    assert result[0]["text"] == "text 0"


# ── Multi-regulation retrieval ────────────────────────────────────────────────


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_multi_regulation_splits_slots(
    mock_embed: MagicMock, mock_conn: MagicMock
) -> None:
    mock_embed.return_value = [[0.1]]
    gdpr_rows = _make_rows(5, "GDPR")
    nis2_rows = _make_rows(5, "NIS2")
    # 2 regulations × 3 legs = 6 fetchall calls
    mock_conn.return_value = _mock_conn(
        [gdpr_rows, gdpr_rows, gdpr_rows, nis2_rows, nis2_rows, nis2_rows]
    )

    result = retrieve("differences between GDPR and NIS2", top_k=4)

    regulations = {c["metadata"]["regulation"] for c in result}
    assert "GDPR" in regulations
    assert "NIS2" in regulations


@patch("rag.retriever.client._get_pgvector_conn")
@patch("rag.retriever.embedder.embed")
def test_retrieve_single_regulation_uses_no_filter(
    mock_embed: MagicMock, mock_conn: MagicMock
) -> None:
    mock_embed.return_value = [[0.1]]
    rows = _make_rows(3)
    conn_mock = _mock_conn([rows, rows, rows])
    mock_conn.return_value = conn_mock

    retrieve("What does GDPR say about consent?", top_k=3)

    # All 3 execute calls should have no regulation filter in their params
    cur = conn_mock.cursor.return_value
    for c in cur.execute.call_args_list:
        args = c[0]
        params = args[1] if len(args) > 1 else ()
        assert "GDPR" not in params

"""Integration test: embed a real query via Bedrock Titan, retrieve from pgvector.

Requires AWS credentials + pgvector with data loaded: task ingest
"""

import pytest

from rag.retriever import retrieve

pytestmark = pytest.mark.integration


def test_retrieve_returns_list() -> None:
    result = retrieve("What does Article 32 of GDPR require?", top_k=3)
    assert isinstance(result, list)


def test_retrieve_chunk_shape() -> None:
    result = retrieve("data breach notification obligations", top_k=3)
    assert len(result) > 0
    for chunk in result:
        assert "text" in chunk
        assert "metadata" in chunk
        assert "score" in chunk
        assert isinstance(chunk["text"], str)
        assert isinstance(chunk["score"], float)
        assert 0.0 <= chunk["score"] <= 1.0


def test_retrieve_respects_top_k() -> None:
    result = retrieve("GDPR controller obligations", top_k=5)
    assert len(result) <= 5


def test_retrieve_gdpr_articles_have_metadata() -> None:
    result = retrieve("consent requirements under GDPR", top_k=3)
    assert len(result) > 0
    for chunk in result:
        assert "regulation" in chunk["metadata"]


def test_retrieve_rrf_ranks_relevant_first() -> None:
    result = retrieve("Article 32 security of processing", top_k=5)
    assert len(result) > 0
    # Top result should mention Article 32 or security
    top_text = result[0]["text"].lower()
    assert any(kw in top_text for kw in ("32", "security", "processing", "appropriate"))

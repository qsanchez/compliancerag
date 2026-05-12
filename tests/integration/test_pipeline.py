"""Integration test: call rag.pipeline.run() end-to-end against real infra.

Requires AWS credentials (Bedrock + pgvector with data loaded): task ingest
"""

import pytest

from rag import pipeline

pytestmark = pytest.mark.integration


def test_pipeline_returns_non_empty_answer() -> None:
    result = pipeline.run("What does Article 32 of GDPR require?")
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 10


def test_pipeline_returns_citations() -> None:
    result = pipeline.run("What are the GDPR requirements for data breach notification?")
    assert isinstance(result["citations"], list)


def test_pipeline_returns_chunks() -> None:
    result = pipeline.run("What are the obligations of a data controller under GDPR?")
    assert isinstance(result["chunks"], list)
    assert len(result["chunks"]) > 0


def test_pipeline_multi_turn_history() -> None:
    history = [
        {"role": "user", "content": "What is GDPR?"},
        {"role": "assistant", "content": "GDPR is the General Data Protection Regulation."},
    ]
    result = pipeline.run("What are the main obligations for controllers?", history=history)
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 10


def test_pipeline_nis2_question() -> None:
    result = pipeline.run("What are the NIS2 obligations for essential entities?")
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 10

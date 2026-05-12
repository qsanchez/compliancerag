"""Integration test: ingest a small fixture batch into real pgvector.

Requires local infra running: task local_infra:up
"""

import pytest

from ingestion.chunker import Chunk
from vectorstore import client

pytestmark = pytest.mark.integration

_FIXTURE_CHUNKS: list[Chunk] = [
    {
        "id": "test-gdpr-art-1-0",
        "text": "This Regulation lays down rules relating to the protection of natural persons.",
        "metadata": {
            "article_number": "Article 1",
            "regulation": "GDPR",
            "title": "Subject-matter",
            "chapter": "Chapter I",
            "source_id": "test-gdpr-art-1",
        },
    },
    {
        "id": "test-gdpr-art-2-0",
        "text": "This Regulation applies to the processing of personal data by automated means.",
        "metadata": {
            "article_number": "Article 2",
            "regulation": "GDPR",
            "title": "Material scope",
            "chapter": "Chapter I",
            "source_id": "test-gdpr-art-2",
        },
    },
]

_FIXTURE_EMBEDDINGS = [[0.1] * 1024, [0.2] * 1024]


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            ids = [c["id"] for c in _FIXTURE_CHUNKS]
            cur.execute("DELETE FROM embeddings WHERE id = ANY(%s)", (ids,))
        conn.commit()


def test_index_inserts_rows() -> None:
    from ingestion.indexer import index

    index(_FIXTURE_CHUNKS, _FIXTURE_EMBEDDINGS)

    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM embeddings WHERE id = ANY(%s)",
                ([c["id"] for c in _FIXTURE_CHUNKS],),
            )
            rows = cur.fetchall()

    assert len(rows) == len(_FIXTURE_CHUNKS)


def test_index_upserts_on_conflict() -> None:
    from ingestion.indexer import index

    index(_FIXTURE_CHUNKS, _FIXTURE_EMBEDDINGS)
    # Second call must not raise (ON CONFLICT DO UPDATE)
    index(_FIXTURE_CHUNKS, _FIXTURE_EMBEDDINGS)

    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM embeddings WHERE id = ANY(%s)",
                ([c["id"] for c in _FIXTURE_CHUNKS],),
            )
            (count,) = cur.fetchone()  # type: ignore[misc]

    assert count == len(_FIXTURE_CHUNKS)


def test_index_stores_metadata() -> None:
    from ingestion.indexer import index

    index(_FIXTURE_CHUNKS, _FIXTURE_EMBEDDINGS)

    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT metadata FROM embeddings WHERE id = %s",
                (_FIXTURE_CHUNKS[0]["id"],),
            )
            row = cur.fetchone()

    assert row is not None
    assert row[0]["regulation"] == "GDPR"

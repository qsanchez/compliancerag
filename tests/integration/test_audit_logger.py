"""Integration test: write an AuditRecord to real Postgres and query audit_log.

Requires local infra running: task local_infra:up
"""

import pytest

from audit.logger import AuditRecord, log_query
from vectorstore import client

pytestmark = pytest.mark.integration

_TEST_QUESTION = "__integration_test_question__"


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log WHERE question = %s", (_TEST_QUESTION,))
        conn.commit()


def test_log_query_inserts_row() -> None:
    record = AuditRecord(
        question=_TEST_QUESTION,
        route="rag",
        answer="Test answer.",
        citations=["Art. 32, GDPR"],
    )
    log_query(record)

    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT question, route, answer FROM audit_log WHERE question = %s",
                (_TEST_QUESTION,),
            )
            row = cur.fetchone()

    assert row is not None
    assert row[0] == _TEST_QUESTION
    assert row[1] == "rag"
    assert row[2] == "Test answer."


def test_log_query_stores_citations() -> None:
    citations = ["Art. 5, GDPR", "Art. 32, GDPR"]
    record = AuditRecord(question=_TEST_QUESTION, citations=citations)
    log_query(record)

    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT citations FROM audit_log WHERE question = %s",
                (_TEST_QUESTION,),
            )
            row = cur.fetchone()

    assert row is not None
    assert row[0] == citations


def test_log_query_injection_blocked_flag() -> None:
    record = AuditRecord(question=_TEST_QUESTION, injection_blocked=True)
    log_query(record)

    with client._get_pgvector_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT injection_blocked FROM audit_log WHERE question = %s",
                (_TEST_QUESTION,),
            )
            row = cur.fetchone()

    assert row is not None
    assert row[0] is True

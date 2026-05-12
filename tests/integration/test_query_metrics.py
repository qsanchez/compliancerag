"""Integration test: run a real SELECT against the Athena fines table.

Requires AWS credentials + Athena table loaded: task analytics:load
"""

import pytest

from analytics_query.query_metrics import _run_query, _validate_sql, query_metrics

pytestmark = pytest.mark.integration


def test_validate_sql_accepts_select() -> None:
    _validate_sql("SELECT country, SUM(fine_amount_eur) FROM gdpr_fines GROUP BY country")


def test_validate_sql_rejects_drop() -> None:
    with pytest.raises(ValueError, match="Forbidden keyword"):
        _validate_sql("DROP TABLE gdpr_fines")


def test_validate_sql_rejects_non_select() -> None:
    with pytest.raises(ValueError, match="Only SELECT"):
        _validate_sql("SHOW TABLES")


def test_run_query_returns_rows() -> None:
    from config import get_settings

    settings = get_settings()
    db = settings.athena_database
    tbl = settings.athena_table_fines
    sql = f"SELECT country, COUNT(*) as cnt FROM {db}.{tbl} GROUP BY country LIMIT 5"
    rows = _run_query(sql)
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert "country" in rows[0]


def test_run_query_row_schema() -> None:
    from config import get_settings

    settings = get_settings()
    db = settings.athena_database
    tbl = settings.athena_table_fines
    sql = f"SELECT * FROM {db}.{tbl} LIMIT 1"
    rows = _run_query(sql)
    assert len(rows) == 1
    row = rows[0]
    for field in ("country", "fine_amount_eur", "controller"):
        assert field in row


def test_query_metrics_end_to_end() -> None:
    result = query_metrics("How many GDPR fines were issued per country?")
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 10
    assert isinstance(result["rows"], list)
    assert isinstance(result["sql"], str)
    assert result["sql"].upper().startswith("SELECT")

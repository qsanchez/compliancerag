import pytest

from agent.tools.query_metrics import _validate_sql


def test_select_query_passes() -> None:
    _validate_sql("SELECT country, SUM(fine_amount_eur) FROM gdpr_fines GROUP BY country")


def test_select_with_where_passes() -> None:
    _validate_sql("SELECT * FROM gdpr_fines WHERE year(decision_date) = 2023 LIMIT 10")


def test_drop_table_rejected() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        _validate_sql("DROP TABLE gdpr_fines")


def test_insert_rejected() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        _validate_sql("INSERT INTO gdpr_fines VALUES ('2024-01-01', 'DE', 'BfDI', 1000000)")


def test_update_rejected() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        _validate_sql("UPDATE gdpr_fines SET fine_amount_eur = 0 WHERE country = 'DE'")


def test_delete_rejected() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        _validate_sql("DELETE FROM gdpr_fines WHERE fine_amount_eur < 1000")


def test_create_table_rejected() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        _validate_sql("CREATE TABLE evil AS SELECT * FROM gdpr_fines")


def test_alter_rejected() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        _validate_sql("ALTER TABLE gdpr_fines ADD COLUMN secret VARCHAR")


def test_truncate_rejected() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        _validate_sql("TRUNCATE TABLE gdpr_fines")


def test_non_select_start_rejected() -> None:
    with pytest.raises(ValueError, match="Only SELECT"):
        _validate_sql("EXPLAIN SELECT * FROM gdpr_fines")


def test_injection_via_subquery_select_allowed() -> None:
    # Subqueries that start with SELECT are fine
    _validate_sql(
        "SELECT * FROM gdpr_fines WHERE fine_amount_eur = "
        "(SELECT MAX(fine_amount_eur) FROM gdpr_fines)"
    )

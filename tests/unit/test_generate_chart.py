import base64

from analytics_query.generate_chart import generate_chart


def _year_rows() -> list[dict]:
    return [
        {"year": "2019", "total_eur": "50000000"},
        {"year": "2020", "total_eur": "115700000"},
        {"year": "2021", "total_eur": "981700000"},
        {"year": "2022", "total_eur": "463000000"},
        {"year": "2023", "total_eur": "1605240000"},
    ]


def _country_rows() -> list[dict]:
    return [
        {"country": "IE", "total_eur": "2035000000"},
        {"country": "LU", "total_eur": "746000000"},
        {"country": "IT", "total_eur": "109350000"},
        {"country": "DE", "total_eur": "72298708"},
        {"country": "FR", "total_eur": "420150000"},
    ]


def test_returns_none_for_empty_rows() -> None:
    assert generate_chart({"rows": []}) is None


def test_returns_none_for_missing_rows_key() -> None:
    assert generate_chart({}) is None


def test_line_chart_for_year_data_returns_base64() -> None:
    result = generate_chart({"rows": _year_rows()})
    assert result is not None
    decoded = base64.b64decode(result)
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


def test_bar_chart_for_country_data_returns_base64() -> None:
    result = generate_chart({"rows": _country_rows()})
    assert result is not None
    decoded = base64.b64decode(result)
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


def test_line_chart_result_is_valid_base64_string() -> None:
    result = generate_chart({"rows": _year_rows()})
    assert isinstance(result, str)
    base64.b64decode(result)  # should not raise


def test_returns_none_when_no_numeric_column() -> None:
    rows = [{"country": "DE", "sector": "Tech"}, {"country": "FR", "sector": "Finance"}]
    assert generate_chart({"rows": rows}) is None

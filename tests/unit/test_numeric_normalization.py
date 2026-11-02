import pytest

from pe_analyst.document_intelligence.service import parse_numeric_value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,000", 1000.0),
        ("$1,234.50", 1234.50),
        ("(900)", -900.0),
        ("(1,234)", -1234.0),
        ("12%", 12.0),
        ("42", 42.0),
        ("-5.5", -5.5),
    ],
)
def test_parse_numeric_value_handles_common_formats(raw: str, expected: float) -> None:
    assert parse_numeric_value(raw) == expected


@pytest.mark.parametrize("raw", ["", "-", "—", "–", "n/a", "N/A", "NM", "Revenue"])
def test_parse_numeric_value_returns_none_for_non_numeric_text(raw: str) -> None:
    assert parse_numeric_value(raw) is None

from datetime import date, datetime

from app.utils.parsing import (
    parse_excel_date,
    parse_int_or_none,
    sanitize_input_text,
    sanitize_metadata_payload,
)


def test_sanitize_input_text_trims_and_limits():
    assert sanitize_input_text("  test  ") == "test"
    assert sanitize_input_text("abcdef", max_length=3) == "abc"
    assert sanitize_input_text(None) == ""


def test_sanitize_metadata_payload_accepts_only_mapping_values():
    assert sanitize_metadata_payload({" key ": " value ", "": "ignored"}) == {"key": "value"}
    assert sanitize_metadata_payload(None) == {}


def test_parse_excel_date_supports_common_formats():
    assert parse_excel_date(date(2026, 1, 2)) == date(2026, 1, 2)
    assert parse_excel_date(datetime(2026, 1, 2, 12, 30)) == date(2026, 1, 2)
    assert parse_excel_date("2026-01-02") == date(2026, 1, 2)
    assert parse_excel_date("02.01.2026") == date(2026, 1, 2)
    assert parse_excel_date("02/01/2026") == date(2026, 1, 2)
    assert parse_excel_date("bad") is None


def test_parse_int_or_none_handles_valid_and_invalid_values():
    assert parse_int_or_none(12) == 12
    assert parse_int_or_none(" 12 ") == 12
    assert parse_int_or_none("") is None
    assert parse_int_or_none("abc") is None
    assert parse_int_or_none(None) is None

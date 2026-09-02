from datetime import date, datetime

from app.utils.parsing import parse_excel_date, parse_int_or_none, sanitize_input_text, sanitize_metadata_payload


def test_sanitize_input_text_strips_and_limits():
    assert sanitize_input_text("  abc  ") == "abc"
    assert sanitize_input_text("abcdef", max_length=3) == "abc"
    assert sanitize_input_text(None) == ""


def test_sanitize_metadata_payload_handles_non_dict():
    assert sanitize_metadata_payload(None) == {}
    assert sanitize_metadata_payload({" key ": " value ", "": "ignored"}) == {"key": "value"}


def test_parse_excel_date_supports_common_formats():
    assert parse_excel_date(datetime(2026, 1, 2, 3, 4)) == date(2026, 1, 2)
    assert parse_excel_date("2026-01-02") == date(2026, 1, 2)
    assert parse_excel_date("02.01.2026") == date(2026, 1, 2)
    assert parse_excel_date("02/01/2026") == date(2026, 1, 2)
    assert parse_excel_date("bad") is None


def test_parse_int_or_none_is_strict():
    assert parse_int_or_none(5) == 5
    assert parse_int_or_none(" 12 ") == 12
    assert parse_int_or_none("") is None
    assert parse_int_or_none("12.5") is None

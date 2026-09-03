from datetime import date
from decimal import Decimal

from app.services.validation import (
    non_negative_decimal,
    non_negative_int,
    one_of,
    optional_text,
    positive_int,
    required_text,
    validate_date,
    validate_email,
    validate_password,
)


def test_required_text_trims_and_rejects_empty():
    assert required_text("  abc  ", "Ad") == ("abc", None)
    value, error = required_text("   ", "Ad")
    assert value is None
    assert error == "Ad zorunludur."


def test_required_text_enforces_max_length():
    value, error = required_text("abcdef", "Kod", max_length=3)
    assert value is None
    assert error == "Kod en fazla 3 karakter olabilir."


def test_optional_text_is_bounded():
    assert optional_text("  abc  ") == "abc"
    assert optional_text("abcdef", max_length=3) == "abc"


def test_positive_and_non_negative_integers():
    assert positive_int("5", "Adet") == (5, None)
    assert positive_int("0", "Adet")[0] is None
    assert non_negative_int("0", "Adet") == (0, None)
    assert non_negative_int("-1", "Adet")[0] is None


def test_validate_email_accepts_normal_address():
    assert validate_email("  user@example.com  ") == ("user@example.com", None)


def test_validate_email_rejects_invalid_address():
    value, error = validate_email("not-an-email")
    assert value is None
    assert error == "Geçerli bir e-posta adresi girin."


def test_validate_password_preserves_whitespace():
    password, error = validate_password("  güçlü şifre  ", username="admin")
    assert password == "  güçlü şifre  "
    assert error is None


def test_validate_password_rejects_username_and_short_values():
    assert validate_password("admin", username="ADMIN")[0] is None
    assert validate_password("1234567")[0] is None


def test_one_of_normalizes_allowed_values():
    assert one_of(" AKTIF ", "Durum", ["aktif", "pasif"]) == ("aktif", None)
    assert one_of("bilinmeyen", "Durum", ["aktif", "pasif"])[0] is None


def test_validate_date_supports_iso_and_local_formats():
    assert validate_date("2026-09-03", "Tarih") == (date(2026, 9, 3), None)
    assert validate_date("03.09.2026", "Tarih") == (date(2026, 9, 3), None)


def test_non_negative_decimal_normalizes_scale():
    assert non_negative_decimal("12,5", "Maliyet") == (Decimal("12.50"), None)
    assert non_negative_decimal("-1", "Maliyet")[0] is None

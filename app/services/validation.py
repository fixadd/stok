from __future__ import annotations

import re
from typing import Any


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def required_text(value: Any, field_name: str, *, max_length: int = 256) -> tuple[str | None, str | None]:
    text = "" if value is None else str(value).strip()
    if not text:
        return None, f"{field_name} zorunludur."
    if len(text) > max_length:
        return None, f"{field_name} en fazla {max_length} karakter olabilir."
    return text, None


def optional_text(value: Any, *, max_length: int = 256) -> str:
    text = "" if value is None else str(value).strip()
    return text[:max_length]


def validate_email(value: Any) -> tuple[str | None, str | None]:
    email = "" if value is None else str(value).strip()
    if not email:
        return None, "E-posta adresi zorunludur."
    if len(email) > 320:
        return None, "E-posta adresi çok uzun."
    if not EMAIL_PATTERN.fullmatch(email):
        return None, "Geçerli bir e-posta adresi girin."
    return email, None


def validate_password(value: Any, *, username: str = "", min_length: int = 8) -> tuple[str | None, str | None]:
    password = "" if value is None else str(value)
    if not password:
        return None, "Şifre zorunludur."
    if len(password) < min_length:
        return None, f"Şifre en az {min_length} karakter olmalıdır."
    if username and password.casefold() == username.casefold():
        return None, "Şifreniz kullanıcı adınızla aynı olamaz."
    return password, None


def positive_int(value: Any, field_name: str) -> tuple[int | None, str | None]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name} geçerli bir sayı olmalıdır."
    if number <= 0:
        return None, f"{field_name} sıfırdan büyük olmalıdır."
    return number, None


def non_negative_int(value: Any, field_name: str) -> tuple[int | None, str | None]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name} geçerli bir sayı olmalıdır."
    if number < 0:
        return None, f"{field_name} negatif olamaz."
    return number, None

from __future__ import annotations

from typing import Any


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

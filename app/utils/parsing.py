from __future__ import annotations

from datetime import date, datetime
from typing import Any


def sanitize_input_text(value: Any, *, max_length: int = 256) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if max_length > 0:
        text = text[:max_length]
    return text


def sanitize_metadata_payload(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    return {
        sanitize_input_text(key, max_length=64): sanitize_input_text(value, max_length=256)
        for key, value in payload.items()
        if sanitize_input_text(key, max_length=64)
    }


def parse_excel_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None

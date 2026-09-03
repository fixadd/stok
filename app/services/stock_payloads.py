from __future__ import annotations

from typing import Any, Mapping


def prepare_stock_metadata(
    category: str,
    payload: Any,
    *,
    schema: Mapping[str, list[dict[str, Any]]],
    defaults: dict[str, Any] | None = None,
    include_assignment_fields: bool = True,
) -> dict[str, str]:
    """Normalize a stock form payload against DB-backed field metadata.

    The caller supplies the active metadata schema so this helper has no
    dependency on the legacy Flask module or on hard-coded field definitions.
    """
    fields = list(schema.get(category, []))
    if not include_assignment_fields:
        fields = [field for field in fields if not field.get("assignment_only")]

    provided: dict[str, Any] = payload if isinstance(payload, dict) else {}
    defaults = defaults or {}
    cleaned: dict[str, str] = {}

    def normalize_value(raw: Any) -> str:
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw.strip()
        return str(raw).strip()

    for field in fields:
        key = field["key"]
        label = field.get("label", key.capitalize())
        value = normalize_value(provided.get(key))
        if not value:
            value = normalize_value(defaults.get(key))
        if not value and field.get("required"):
            raise ValueError(f"{label} alanı zorunludur.")
        if value:
            cleaned[key] = value

    for key, value in provided.items():
        if key in cleaned:
            continue
        normalized = normalize_value(value)
        if normalized:
            cleaned[key] = normalized

    return cleaned


def json_error(message: str) -> dict[str, str]:
    """Return the application's standard JSON error payload."""
    return {"error": message}

"""Framework services for enterprise features.

The service layer is intentionally Flask-route agnostic. Route modules can use
these builders while legacy.py is being retired.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable


@dataclass(frozen=True)
class FilterRule:
    field: str
    operator: str
    value: Any = None


@dataclass(frozen=True)
class FilterSpec:
    rules: tuple[FilterRule, ...] = ()
    match: str = "all"

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "FilterSpec":
        payload = payload or {}
        match = str(payload.get("match", "all")).lower()
        if match not in {"all", "any"}:
            raise ValueError("Filtre eşleştirme tipi all veya any olmalıdır.")
        rules = []
        for raw in payload.get("rules", []):
            field = str(raw.get("field", "")).strip()
            operator = str(raw.get("operator", "eq")).strip().lower()
            if not field:
                continue
            rules.append(FilterRule(field, operator, raw.get("value")))
        return cls(tuple(rules), match)


def apply_filter_rules(items: Iterable[Any], spec: FilterSpec, getter=None) -> list[Any]:
    """Apply portable filters to model objects or dictionaries."""
    getter = getter or (lambda item, key: item.get(key) if isinstance(item, dict) else getattr(item, key, None))

    def matches(item: Any, rule: FilterRule) -> bool:
        actual = getter(item, rule.field)
        expected = rule.value
        if rule.operator == "eq": return actual == expected
        if rule.operator == "neq": return actual != expected
        if rule.operator == "contains": return str(expected).lower() in str(actual or "").lower()
        if rule.operator == "starts_with": return str(actual or "").lower().startswith(str(expected).lower())
        if rule.operator == "ends_with": return str(actual or "").lower().endswith(str(expected).lower())
        if rule.operator == "in": return actual in (expected or [])
        if rule.operator == "not_in": return actual not in (expected or [])
        if rule.operator == "is_empty": return actual in (None, "", [])
        if rule.operator == "not_empty": return actual not in (None, "", [])
        if rule.operator in {"gt", "gte", "lt", "lte"}:
            try:
                return {"gt": actual > expected, "gte": actual >= expected, "lt": actual < expected, "lte": actual <= expected}[rule.operator]
            except TypeError:
                return False
        raise ValueError(f"Desteklenmeyen filtre operatörü: {rule.operator}")

    rules = spec.rules
    return [item for item in items if (all(matches(item, r) for r in rules) if spec.match == "all" else any(matches(item, r) for r in rules))]


@dataclass(frozen=True)
class ReportSpec:
    entity: str
    fields: tuple[str, ...]
    filters: FilterSpec = field(default_factory=FilterSpec)
    sort: tuple[tuple[str, str], ...] = ()
    group_by: tuple[str, ...] = ()
    date_field: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ReportSpec":
        entity = str(payload.get("entity", "")).strip()
        fields = tuple(str(x).strip() for x in payload.get("fields", []) if str(x).strip())
        if not entity or not fields:
            raise ValueError("Rapor için varlık ve en az bir alan gereklidir.")
        sort = tuple((str(x.get("field")), str(x.get("direction", "asc")).lower()) for x in payload.get("sort", []))
        if any(direction not in {"asc", "desc"} for _, direction in sort):
            raise ValueError("Sıralama yönü asc veya desc olmalıdır.")
        return cls(entity, fields, FilterSpec.from_payload(payload.get("filters")), sort, tuple(payload.get("group_by", [])), payload.get("date_field"))


def serialize_report_rows(rows: Iterable[Any], spec: ReportSpec, getter=None) -> list[dict[str, Any]]:
    getter = getter or (lambda item, key: item.get(key) if isinstance(item, dict) else getattr(item, key, None))
    return [{field: getter(row, field) for field in spec.fields} for row in rows]


@dataclass(frozen=True)
class NotificationPlan:
    category: str
    title: str
    message: str
    channels: tuple[str, ...] = ("web",)
    due_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def build_notification_plan(category: str, title: str, message: str, *, due_at: datetime | None = None, channels: Iterable[str] = ("web",), metadata: dict[str, Any] | None = None) -> NotificationPlan:
    allowed = {"web", "email", "telegram"}
    selected = tuple(dict.fromkeys(str(channel).lower() for channel in channels if str(channel).lower() in allowed)) or ("web",)
    return NotificationPlan(category=str(category).strip(), title=str(title).strip(), message=str(message).strip(), channels=selected, due_at=due_at, metadata=metadata or {})


TOKEN_PREFIX = "stk_"


def create_api_token(*, ttl_days: int = 90) -> tuple[str, str, datetime]:
    if ttl_days < 1 or ttl_days > 3650:
        raise ValueError("Token süresi 1-3650 gün arasında olmalıdır.")
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, digest, datetime.utcnow() + timedelta(days=ttl_days)


def hash_api_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(token: str, token_hash: str, expires_at: datetime | None = None) -> bool:
    if not token or not token_hash:
        return False
    if expires_at is not None and expires_at <= datetime.utcnow():
        return False
    return secrets.compare_digest(hash_api_token(token), token_hash)

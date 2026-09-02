from __future__ import annotations

from typing import Any

from ..queries import maintenance_queries, maintenance_extended_queries
from .responses import ok


def get_item(item_id: int) -> dict[str, Any]:
    return ok(item=maintenance_queries.get_item(item_id))


def get_record(item_id: int, maintenance_id: int) -> dict[str, Any]:
    return ok(record=maintenance_queries.get_record(item_id, maintenance_id))


def list_records(item_id: int, *, limit: int = 500) -> dict[str, Any]:
    return ok(records=maintenance_queries.list_records(item_id, limit=limit))


def list_items(*, limit: int = 500) -> dict[str, Any]:
    return ok(items=maintenance_queries.list_items(limit=limit))


def list_recent(*, limit: int = 100) -> dict[str, Any]:
    return ok(records=maintenance_extended_queries.list_recent(limit=limit))


def list_by_performer(performer: str, *, limit: int = 500) -> dict[str, Any]:
    return ok(records=maintenance_extended_queries.list_by_performer(performer, limit=limit))

from __future__ import annotations

from typing import Any

from ..queries import inventory_event_queries
from .responses import ok


def list_events(*, limit: int = 500) -> dict[str, Any]:
    return ok(events=inventory_event_queries.list_events(limit=limit))


def list_item_events(item_id: int, *, limit: int = 100) -> dict[str, Any]:
    return ok(events=inventory_event_queries.list_item_events(item_id, limit=limit))

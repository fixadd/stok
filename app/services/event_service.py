from __future__ import annotations

from typing import Any

from ..queries import inventory_event_queries
from .responses import ok


EVENT_TYPES = {
    "INVENTORY_CREATED": "INVENTORY_CREATED",
    "INVENTORY_ASSIGNED": "INVENTORY_ASSIGNED",
    "INVENTORY_RETURNED": "INVENTORY_RETURNED",
    "INVENTORY_SENT_TO_STOCK": "INVENTORY_SENT_TO_STOCK",
    "INVENTORY_SCRAPPED": "INVENTORY_SCRAPPED",
    "MAINTENANCE_CREATED": "MAINTENANCE_CREATED",
    "MAINTENANCE_UPDATED": "MAINTENANCE_UPDATED",
    "MAINTENANCE_DELETED": "MAINTENANCE_DELETED",
    "REPAIR_CREATED": "REPAIR_CREATED",
    "REPAIR_SENT": "REPAIR_SENT",
    "REPAIR_COMPLETED": "REPAIR_COMPLETED",
    "REPAIR_RETURNED": "REPAIR_RETURNED",
    "LICENSE_ASSIGNED": "LICENSE_ASSIGNED",
    "LICENSE_DEACTIVATED": "LICENSE_DEACTIVATED",
    "STOCK_IN": "STOCK_IN",
    "STOCK_OUT": "STOCK_OUT",
}


def normalize_event_type(value: str) -> str:
    """Return a stable event identifier for new audit records."""
    normalized = (value or "").strip().upper().replace(" ", "_")
    return EVENT_TYPES.get(normalized, normalized)


def list_events(*, limit: int = 500) -> dict[str, Any]:
    return ok(events=inventory_event_queries.list_events(limit=limit))


def list_item_events(item_id: int, *, limit: int = 100) -> dict[str, Any]:
    return ok(events=inventory_event_queries.list_item_events(item_id, limit=limit))

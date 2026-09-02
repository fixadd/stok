from __future__ import annotations

from sqlalchemy import func

from ..models import InventoryEvent
from .common import apply_limit


def get_event(event_id: int | None) -> InventoryEvent | None:
    if event_id is None:
        return None
    return InventoryEvent.query.filter(InventoryEvent.id == event_id).first()


def list_item_events(item_id: int | None, *, limit: int = 100) -> list[InventoryEvent]:
    if item_id is None:
        return []
    query = (
        InventoryEvent.query
        .filter(InventoryEvent.item_id == item_id)
        .order_by(InventoryEvent.performed_at.desc(), InventoryEvent.id.desc())
    )
    return apply_limit(query, limit=limit).all()


def list_events(*, limit: int = 500) -> list[InventoryEvent]:
    query = InventoryEvent.query.order_by(
        InventoryEvent.performed_at.desc(), InventoryEvent.id.desc()
    )
    return apply_limit(query, limit=limit).all()


def list_events_by_type(event_type: str | None, *, limit: int = 500) -> list[InventoryEvent]:
    value = (event_type or "").strip()
    if not value:
        return []
    query = (
        InventoryEvent.query
        .filter(func.lower(InventoryEvent.event_type) == value.lower())
        .order_by(InventoryEvent.performed_at.desc(), InventoryEvent.id.desc())
    )
    return apply_limit(query, limit=limit).all()

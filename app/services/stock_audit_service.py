from __future__ import annotations

from typing import Any

from ..models import StockAuditLog, StockItem, StockLog, StockMovement, User, db
from .activity_service import DEFAULT_EVENT_ACTOR, record_activity


def record_stock_movement(
    stock_item: StockItem,
    *,
    operation_type: str,
    old_quantity: int,
    new_quantity: int,
    user: User | None,
) -> StockMovement:
    """Persist a stock quantity/status movement in the current transaction."""
    movement = StockMovement(
        stock_item=stock_item,
        user_id=user.id if user else None,
        operation_type=operation_type,
        old_quantity=max(0, int(old_quantity)),
        new_quantity=max(0, int(new_quantity)),
    )
    db.session.add(movement)
    return movement


def record_stock_audit(
    stock_item: StockItem,
    *,
    old_quantity: int,
    new_quantity: int,
    performed_by: str,
) -> StockAuditLog:
    """Persist an immutable quantity audit entry."""
    audit = StockAuditLog(
        stock_item=stock_item,
        old_quantity=max(0, int(old_quantity)),
        new_quantity=max(0, int(new_quantity)),
        performed_by=(performed_by or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR,
    )
    db.session.add(audit)
    return audit


def record_stock_log(
    stock_item: StockItem,
    action: str,
    *,
    action_type: str = "info",
    performed_by: str | None = None,
    quantity_change: int = 0,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> StockLog:
    """Persist a stock log and the matching user-visible activity record."""
    actor = (performed_by or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR
    log = StockLog(
        stock_item=stock_item,
        action=action,
        action_type=action_type,
        performed_by=actor,
        quantity_change=quantity_change,
        note=note or None,
    )
    log.metadata_payload = metadata or None
    db.session.add(log)

    activity_metadata = {
        "stock_item_id": stock_item.id,
        "stock_item_title": stock_item.title,
        "stock_item_status": stock_item.status,
    }
    if metadata:
        activity_metadata.update(metadata)

    record_activity(
        area="stok",
        action=action,
        description=note or stock_item.title,
        actor=actor,
        metadata=activity_metadata,
    )
    return log

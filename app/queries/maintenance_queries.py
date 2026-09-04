from __future__ import annotations

from ..models import InventoryItem, InventoryMaintenance
from .common import apply_limit


def get_item(item_id: int) -> InventoryItem | None:
    return InventoryItem.query.filter_by(id=item_id).first()


def get_record(item_id: int, maintenance_id: int) -> InventoryMaintenance | None:
    return InventoryMaintenance.query.filter_by(
        id=maintenance_id,
        item_id=item_id,
    ).first()


def list_records(item_id: int, *, limit: int = 500) -> list[InventoryMaintenance]:
    query = (
        InventoryMaintenance.query
        .filter_by(item_id=item_id)
        .order_by(
            InventoryMaintenance.performed_at.desc(),
            InventoryMaintenance.id.desc(),
        )
    )
    return apply_limit(query, limit=limit).all()


def list_items(*, limit: int = 500) -> list[InventoryItem]:
    query = InventoryItem.query.order_by(InventoryItem.inventory_no)
    return apply_limit(query, limit=limit).all()

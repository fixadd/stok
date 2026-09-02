from __future__ import annotations

from ..models import InventoryItem, InventoryMaintenance


def get_item(item_id: int) -> InventoryItem | None:
    return InventoryItem.query.get(item_id)


def get_record(item_id: int, maintenance_id: int) -> InventoryMaintenance | None:
    return InventoryMaintenance.query.filter_by(
        id=maintenance_id,
        item_id=item_id,
    ).first()


def list_records(item_id: int) -> list[InventoryMaintenance]:
    return (
        InventoryMaintenance.query
        .filter_by(item_id=item_id)
        .order_by(
            InventoryMaintenance.performed_at.desc(),
            InventoryMaintenance.id.desc(),
        )
        .all()
    )


def list_items() -> list[InventoryItem]:
    return InventoryItem.query.order_by(InventoryItem.inventory_no).all()

from __future__ import annotations

from ..models import InventoryItem
from ..repair_model import InventoryRepair
from .common import apply_limit


def get_item(item_id: int) -> InventoryItem | None:
    return InventoryItem.query.get(item_id)


def get_record(item_id: int, repair_id: int) -> InventoryRepair | None:
    return InventoryRepair.query.filter_by(
        id=repair_id,
        item_id=item_id,
    ).first()


def list_records(item_id: int | None = None, *, limit: int = 500) -> list[InventoryRepair]:
    query = InventoryRepair.query
    if item_id is not None:
        query = query.filter(InventoryRepair.item_id == item_id)
    query = query.order_by(
        InventoryRepair.fault_date.desc(),
        InventoryRepair.id.desc(),
    )
    return apply_limit(query, limit=limit).all()


def get_latest_record(item_id: int) -> InventoryRepair | None:
    return (
        InventoryRepair.query
        .filter(InventoryRepair.item_id == item_id)
        .order_by(
            InventoryRepair.fault_date.desc(),
            InventoryRepair.id.desc(),
        )
        .first()
    )


def list_items(*, limit: int = 500) -> list[InventoryItem]:
    query = InventoryItem.query.order_by(InventoryItem.inventory_no)
    return apply_limit(query, limit=limit).all()

from __future__ import annotations

from sqlalchemy import func

from ..models import InventoryItem
from .common import apply_limit


def base_inventory_query(*, include_scrap: bool = False):
    query = InventoryItem.query
    if not include_scrap:
        query = query.filter(func.lower(InventoryItem.status) != "hurda")
    return query


def get_item(item_id: int | None, *, include_scrap: bool = False) -> InventoryItem | None:
    if item_id is None:
        return None
    return (
        base_inventory_query(include_scrap=include_scrap)
        .filter(InventoryItem.id == item_id)
        .first()
    )


def get_by_inventory_no(
    inventory_no: str | None, *, include_scrap: bool = False
) -> InventoryItem | None:
    value = (inventory_no or "").strip()
    if not value:
        return None
    return (
        base_inventory_query(include_scrap=include_scrap)
        .filter(func.lower(InventoryItem.inventory_no) == value.lower())
        .first()
    )


def list_by_responsible_user(user_id: int | None, *, limit: int = 500) -> list[InventoryItem]:
    if user_id is None:
        return []
    query = (
        base_inventory_query()
        .filter(InventoryItem.responsible_user_id == user_id)
        .order_by(InventoryItem.inventory_no)
    )
    return apply_limit(query, limit=limit).all()


def list_by_factory(factory_id: int | None, *, limit: int = 500) -> list[InventoryItem]:
    if factory_id is None:
        return []
    query = (
        base_inventory_query()
        .filter(InventoryItem.factory_id == factory_id)
        .order_by(InventoryItem.inventory_no)
    )
    return apply_limit(query, limit=limit).all()


def list_inventory_items(*, limit: int = 500) -> list[InventoryItem]:
    query = base_inventory_query().order_by(InventoryItem.inventory_no)
    return apply_limit(query, limit=limit).all()


def list_scrap_items(*, limit: int = 500) -> list[InventoryItem]:
    query = (
        InventoryItem.query
        .filter(func.lower(InventoryItem.status) == "hurda")
        .order_by(InventoryItem.inventory_no)
    )
    return apply_limit(query, limit=limit).all()


def count_by_status(status: str) -> int:
    normalized = (status or "").strip().lower()
    if not normalized:
        return 0
    return InventoryItem.query.filter(func.lower(InventoryItem.status) == normalized).count()

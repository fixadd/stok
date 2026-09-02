from __future__ import annotations

from sqlalchemy import func

from ..models import StockCategory, StockItem, StockUnit
from .common import apply_limit


def base_item_query(*, include_deleted: bool = False):
    query = StockItem.query
    if not include_deleted:
        query = query.filter(StockItem.is_deleted.is_(False))
    return query


def get_item(item_id: int | None, *, include_deleted: bool = False) -> StockItem | None:
    if item_id is None:
        return None
    return base_item_query(include_deleted=include_deleted).filter(
        StockItem.id == item_id
    ).first()


def get_by_sku(sku: str | None, *, include_deleted: bool = False) -> StockItem | None:
    value = (sku or "").strip()
    if not value:
        return None
    return base_item_query(include_deleted=include_deleted).filter(
        func.lower(StockItem.sku) == value.lower()
    ).first()


def get_by_reference_code(
    reference_code: str | None, *, include_deleted: bool = False
) -> StockItem | None:
    value = (reference_code or "").strip()
    if not value:
        return None
    return base_item_query(include_deleted=include_deleted).filter(
        func.lower(StockItem.reference_code) == value.lower()
    ).first()


def list_items(*, limit: int = 500) -> list[StockItem]:
    query = base_item_query().order_by(func.lower(StockItem.title), StockItem.id)
    return apply_limit(query, limit=limit).all()


def list_low_quantity(*, threshold: int = 0, limit: int = 500) -> list[StockItem]:
    try:
        bounded = max(0, int(threshold))
    except (TypeError, ValueError):
        bounded = 0
    query = base_item_query().filter(StockItem.quantity <= bounded).order_by(
        StockItem.quantity, func.lower(StockItem.title), StockItem.id
    )
    return apply_limit(query, limit=limit).all()


def list_categories(*, limit: int = 100) -> list[StockCategory]:
    query = StockCategory.query.order_by(func.lower(StockCategory.name), StockCategory.id)
    return apply_limit(query, limit=limit).all()


def list_units(*, limit: int = 100) -> list[StockUnit]:
    query = StockUnit.query.order_by(func.lower(StockUnit.name), StockUnit.id)
    return apply_limit(query, limit=limit).all()

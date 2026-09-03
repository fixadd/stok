from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..models import InventoryItem, StockAssignment, StockCategory, StockItem, StockLog, StockMovement, StockUnit
from .common import apply_limit


def base_item_query(*, include_deleted: bool = False):
    query = StockItem.query
    if not include_deleted:
        query = query.filter(StockItem.is_deleted.is_(False))
    return query


def get_item(item_id: int | None, *, include_deleted: bool = False) -> StockItem | None:
    if item_id is None:
        return None
    return base_item_query(include_deleted=include_deleted).filter(StockItem.id == item_id).first()


def get_by_sku(sku: str | None, *, include_deleted: bool = False) -> StockItem | None:
    value = (sku or "").strip()
    if not value:
        return None
    return base_item_query(include_deleted=include_deleted).filter(func.lower(StockItem.sku) == value.lower()).first()


def get_by_reference_code(reference_code: str | None, *, include_deleted: bool = False) -> StockItem | None:
    value = (reference_code or "").strip()
    if not value:
        return None
    return base_item_query(include_deleted=include_deleted).filter(func.lower(StockItem.reference_code) == value.lower()).first()


def list_items(*, limit: int = 500) -> list[StockItem]:
    query = base_item_query().order_by(func.lower(StockItem.title), StockItem.id)
    return apply_limit(query, limit=limit).all()


def list_low_quantity(*, threshold: int = 0, limit: int = 500) -> list[StockItem]:
    try:
        bounded = max(0, int(threshold))
    except (TypeError, ValueError):
        bounded = 0
    query = base_item_query().filter(StockItem.quantity <= bounded).order_by(StockItem.quantity, func.lower(StockItem.title), StockItem.id)
    return apply_limit(query, limit=limit).all()


def list_item_logs(stock_item_id: int | None, *, limit: int = 100) -> list[StockLog]:
    if stock_item_id is None:
        return []
    query = StockLog.query.filter(StockLog.stock_item_id == stock_item_id).order_by(StockLog.created_at.desc(), StockLog.id.desc())
    return apply_limit(query, limit=limit).all()


def list_item_movements(stock_item_id: int | None, *, limit: int = 100) -> list[StockMovement]:
    if stock_item_id is None:
        return []
    query = StockMovement.query.filter(StockMovement.stock_item_id == stock_item_id).order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
    return apply_limit(query, limit=limit).all()


def list_item_assignments(stock_item_id: int | None, *, limit: int = 100) -> list[StockAssignment]:
    if stock_item_id is None:
        return []
    query = StockAssignment.query.filter(StockAssignment.stock_item_id == stock_item_id).order_by(StockAssignment.created_at.desc(), StockAssignment.id.desc())
    return apply_limit(query, limit=limit).all()


def list_categories(*, limit: int = 100) -> list[StockCategory]:
    query = StockCategory.query.order_by(func.lower(StockCategory.name), StockCategory.id)
    return apply_limit(query, limit=limit).all()


def list_units(*, limit: int = 100) -> list[StockUnit]:
    query = StockUnit.query.order_by(func.lower(StockUnit.name), StockUnit.id)
    return apply_limit(query, limit=limit).all()


def list_tracking_items(*, limit: int = 5000) -> list[StockItem]:
    query = base_item_query().options(
        joinedload(StockItem.inventory_item).joinedload(InventoryItem.hardware_type),
        joinedload(StockItem.inventory_item).joinedload(InventoryItem.factory),
        joinedload(StockItem.inventory_item).joinedload(InventoryItem.brand),
        joinedload(StockItem.inventory_item).joinedload(InventoryItem.model),
        joinedload(StockItem.license),
        joinedload(StockItem.category_ref),
        joinedload(StockItem.unit_ref),
        joinedload(StockItem.logs),
    ).order_by(StockItem.created_at.desc())
    return apply_limit(query, limit=limit).all()


def list_recent_logs(*, limit: int = 40) -> list[StockLog]:
    query = StockLog.query.options(joinedload(StockLog.stock_item)).order_by(StockLog.created_at.desc(), StockLog.id.desc())
    return apply_limit(query, limit=limit).all()


def list_recent_assignments(*, limit: int = 100) -> list[StockAssignment]:
    query = StockAssignment.query.order_by(StockAssignment.created_at.desc(), StockAssignment.id.desc())
    return apply_limit(query, limit=limit).all()


def list_scrap_inventory_items(*, limit: int = 5000) -> list[InventoryItem]:
    query = InventoryItem.query.options(
        joinedload(InventoryItem.factory),
        joinedload(InventoryItem.hardware_type),
        joinedload(InventoryItem.brand),
        joinedload(InventoryItem.model),
        joinedload(InventoryItem.responsible_user),
        joinedload(InventoryItem.events),
    ).filter(func.lower(InventoryItem.status) == "hurda").order_by(InventoryItem.updated_at.desc(), InventoryItem.inventory_no)
    return apply_limit(query, limit=limit).all()

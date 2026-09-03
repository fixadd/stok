from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..models import InventoryItem, InventoryLicense
from .common import apply_limit


def get_license(license_id: int | None) -> InventoryLicense | None:
    if license_id is None:
        return None
    return InventoryLicense.query.filter(InventoryLicense.id == license_id).first()


def list_item_licenses(item_id: int | None, *, limit: int = 100) -> list[InventoryLicense]:
    if item_id is None:
        return []
    query = InventoryLicense.query.filter(InventoryLicense.item_id == item_id).order_by(InventoryLicense.id.desc())
    return apply_limit(query, limit=limit).all()


def list_licenses(*, status: str | None = None, limit: int = 500) -> list[InventoryLicense]:
    query = InventoryLicense.query
    normalized = (status or "").strip().lower()
    if normalized:
        query = query.filter(func.lower(InventoryLicense.status) == normalized)
    query = query.order_by(InventoryLicense.id.desc())
    return apply_limit(query, limit=limit).all()


def list_tracking_licenses(*, limit: int = 5000) -> list[InventoryLicense]:
    query = InventoryLicense.query.options(
        joinedload(InventoryLicense.item).joinedload(InventoryItem.responsible_user),
        joinedload(InventoryLicense.item).joinedload(InventoryItem.hardware_type),
        joinedload(InventoryLicense.item).joinedload(InventoryItem.factory),
        joinedload(InventoryLicense.item).joinedload(InventoryItem.events),
    ).order_by(InventoryLicense.id)
    return apply_limit(query, limit=limit).all()

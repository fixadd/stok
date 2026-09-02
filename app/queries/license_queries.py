from __future__ import annotations

from sqlalchemy import func

from ..models import InventoryLicense
from .common import apply_limit


def get_license(license_id: int | None) -> InventoryLicense | None:
    if license_id is None:
        return None
    return InventoryLicense.query.filter(InventoryLicense.id == license_id).first()


def list_item_licenses(item_id: int | None, *, limit: int = 100) -> list[InventoryLicense]:
    if item_id is None:
        return []
    query = (
        InventoryLicense.query
        .filter(InventoryLicense.item_id == item_id)
        .order_by(InventoryLicense.id.desc())
    )
    return apply_limit(query, limit=limit).all()


def list_licenses(*, status: str | None = None, limit: int = 500) -> list[InventoryLicense]:
    query = InventoryLicense.query
    normalized = (status or "").strip().lower()
    if normalized:
        query = query.filter(func.lower(InventoryLicense.status) == normalized)
    query = query.order_by(InventoryLicense.id.desc())
    return apply_limit(query, limit=limit).all()

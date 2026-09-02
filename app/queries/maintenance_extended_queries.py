from __future__ import annotations

from sqlalchemy import func

from ..models import InventoryMaintenance
from .common import apply_limit


def get_maintenance(maintenance_id: int | None) -> InventoryMaintenance | None:
    if maintenance_id is None:
        return None
    return InventoryMaintenance.query.filter(
        InventoryMaintenance.id == maintenance_id
    ).first()


def list_by_performer(performer: str | None, *, limit: int = 500) -> list[InventoryMaintenance]:
    value = (performer or "").strip()
    if not value:
        return []
    query = (
        InventoryMaintenance.query
        .filter(func.lower(InventoryMaintenance.performed_by) == value.lower())
        .order_by(InventoryMaintenance.performed_at.desc(), InventoryMaintenance.id.desc())
    )
    return apply_limit(query, limit=limit).all()


def list_recent(*, limit: int = 100) -> list[InventoryMaintenance]:
    query = InventoryMaintenance.query.order_by(
        InventoryMaintenance.performed_at.desc(), InventoryMaintenance.id.desc()
    )
    return apply_limit(query, limit=limit).all()

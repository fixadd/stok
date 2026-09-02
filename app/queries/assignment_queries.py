from __future__ import annotations

from sqlalchemy import func

from ..models import InventoryAssignment
from .common import apply_limit


def get_assignment(assignment_id: int | None) -> InventoryAssignment | None:
    if assignment_id is None:
        return None
    return InventoryAssignment.query.filter(InventoryAssignment.id == assignment_id).first()


def list_item_assignments(item_id: int | None, *, limit: int = 100) -> list[InventoryAssignment]:
    if item_id is None:
        return []
    query = (
        InventoryAssignment.query
        .filter(InventoryAssignment.item_id == item_id)
        .order_by(InventoryAssignment.assigned_at.desc(), InventoryAssignment.id.desc())
    )
    return apply_limit(query, limit=limit).all()


def list_active_assignments(*, limit: int = 500) -> list[InventoryAssignment]:
    query = (
        InventoryAssignment.query
        .filter(InventoryAssignment.returned_at.is_(None))
        .order_by(func.lower(InventoryAssignment.assigned_to), InventoryAssignment.id.desc())
    )
    return apply_limit(query, limit=limit).all()


def list_user_assignments(user_id: int | None, *, limit: int = 500) -> list[InventoryAssignment]:
    if user_id is None:
        return []
    query = (
        InventoryAssignment.query
        .filter(InventoryAssignment.assigned_user_id == user_id)
        .order_by(InventoryAssignment.assigned_at.desc(), InventoryAssignment.id.desc())
    )
    return apply_limit(query, limit=limit).all()

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..models import RequestGroup, RequestLine, RequestOrder
from .common import apply_limit


def get_group(group_id: int | None) -> RequestGroup | None:
    if group_id is None:
        return None
    return RequestGroup.query.filter(RequestGroup.id == group_id).first()


def get_group_by_key(key: str | None) -> RequestGroup | None:
    value = (key or "").strip()
    if not value:
        return None
    return RequestGroup.query.filter(func.lower(RequestGroup.key) == value.lower()).first()


def list_groups(*, limit: int = 100) -> list[RequestGroup]:
    query = RequestGroup.query.order_by(func.lower(RequestGroup.label), RequestGroup.id)
    return apply_limit(query, limit=limit).all()


def get_order(order_id: int | None) -> RequestOrder | None:
    if order_id is None:
        return None
    return RequestOrder.query.filter(RequestOrder.id == order_id).first()


def get_order_by_number(order_no: str | None) -> RequestOrder | None:
    value = (order_no or "").strip()
    if not value:
        return None
    return RequestOrder.query.filter(func.lower(RequestOrder.order_no) == value.lower()).first()


def list_orders(*, group_id: int | None = None, limit: int = 500) -> list[RequestOrder]:
    query = RequestOrder.query
    if group_id is not None:
        query = query.filter(RequestOrder.group_id == group_id)
    query = query.order_by(RequestOrder.opened_at.desc(), RequestOrder.id.desc())
    return apply_limit(query, limit=limit).all()


def list_orders_by_requester(requested_by: str | None, *, limit: int = 500) -> list[RequestOrder]:
    value = (requested_by or "").strip()
    if not value:
        return []
    query = RequestOrder.query.filter(func.lower(RequestOrder.requested_by) == value.lower()).order_by(RequestOrder.opened_at.desc(), RequestOrder.id.desc())
    return apply_limit(query, limit=limit).all()


def list_orders_by_department(department: str | None, *, limit: int = 500) -> list[RequestOrder]:
    value = (department or "").strip()
    if not value:
        return []
    query = RequestOrder.query.filter(func.lower(RequestOrder.department) == value.lower()).order_by(RequestOrder.opened_at.desc(), RequestOrder.id.desc())
    return apply_limit(query, limit=limit).all()


def list_order_lines(order_id: int | None, *, limit: int = 500) -> list[RequestLine]:
    if order_id is None:
        return []
    query = RequestLine.query.filter(RequestLine.order_id == order_id).order_by(RequestLine.id)
    return apply_limit(query, limit=limit).all()


def list_groups_with_relations(*, limit: int = 100) -> list[RequestGroup]:
    query = RequestGroup.query.options(
        joinedload(RequestGroup.orders).joinedload(RequestOrder.lines),
        joinedload(RequestGroup.orders).joinedload(RequestOrder.snapshots),
    ).order_by(RequestGroup.id)
    return apply_limit(query, limit=limit).all()

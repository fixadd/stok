from __future__ import annotations

from typing import Any

from ..queries import request_queries
from .responses import ok


def get_group(group_id: int) -> dict[str, Any]:
    return ok(group=request_queries.get_group(group_id))


def get_group_by_key(key: str) -> dict[str, Any]:
    return ok(group=request_queries.get_group_by_key(key))


def list_groups(*, limit: int = 100) -> dict[str, Any]:
    return ok(groups=request_queries.list_groups(limit=limit))


def get_order(order_id: int) -> dict[str, Any]:
    return ok(order=request_queries.get_order(order_id))


def get_order_by_number(order_no: str) -> dict[str, Any]:
    return ok(order=request_queries.get_order_by_number(order_no))


def list_orders(*, group_id: int | None = None, limit: int = 500) -> dict[str, Any]:
    return ok(orders=request_queries.list_orders(group_id=group_id, limit=limit))


def list_orders_by_requester(requested_by: str, *, limit: int = 500) -> dict[str, Any]:
    return ok(orders=request_queries.list_orders_by_requester(requested_by, limit=limit))


def list_orders_by_department(department: str, *, limit: int = 500) -> dict[str, Any]:
    return ok(orders=request_queries.list_orders_by_department(department, limit=limit))


def list_order_lines(order_id: int, *, limit: int = 500) -> dict[str, Any]:
    return ok(lines=request_queries.list_order_lines(order_id, limit=limit))

from __future__ import annotations

from typing import Any

from ..queries import inventory_queries
from .responses import ok


def get_item(item_id: int, *, include_scrap: bool = False) -> dict[str, Any]:
    return ok(item=inventory_queries.get_item(item_id, include_scrap=include_scrap))


def get_by_inventory_no(inventory_no: str, *, include_scrap: bool = False) -> dict[str, Any]:
    return ok(item=inventory_queries.get_by_inventory_no(inventory_no, include_scrap=include_scrap))


def list_items(*, limit: int = 500) -> dict[str, Any]:
    return ok(items=inventory_queries.list_inventory_items(limit=limit))


def list_scrap_items(*, limit: int = 500) -> dict[str, Any]:
    return ok(items=inventory_queries.list_scrap_items(limit=limit))


def list_by_responsible_user(user_id: int, *, limit: int = 500) -> dict[str, Any]:
    return ok(items=inventory_queries.list_by_responsible_user(user_id, limit=limit))


def list_by_factory(factory_id: int, *, limit: int = 500) -> dict[str, Any]:
    return ok(items=inventory_queries.list_by_factory(factory_id, limit=limit))


def count_by_status(status: str) -> dict[str, Any]:
    return ok(count=inventory_queries.count_by_status(status))

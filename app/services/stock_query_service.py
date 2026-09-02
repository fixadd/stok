from __future__ import annotations

from typing import Any

from ..queries import inventory_stock_queries
from .responses import ok


def list_stock_items(*, limit: int = 500) -> dict[str, Any]:
    return ok(items=inventory_stock_queries.list_items(limit=limit))


def list_low_quantity(*, threshold: int = 0, limit: int = 500) -> dict[str, Any]:
    return ok(items=inventory_stock_queries.list_low_quantity(threshold=threshold, limit=limit))


def list_categories(*, limit: int = 100) -> dict[str, Any]:
    return ok(categories=inventory_stock_queries.list_categories(limit=limit))


def list_units(*, limit: int = 100) -> dict[str, Any]:
    return ok(units=inventory_stock_queries.list_units(limit=limit))

from __future__ import annotations

from typing import Any

from ..queries import license_queries
from .responses import ok


def list_licenses(*, status: str | None = None, limit: int = 500) -> dict[str, Any]:
    return ok(licenses=license_queries.list_licenses(status=status, limit=limit))


def list_item_licenses(item_id: int, *, limit: int = 100) -> dict[str, Any]:
    return ok(licenses=license_queries.list_item_licenses(item_id, limit=limit))

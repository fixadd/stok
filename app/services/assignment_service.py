from __future__ import annotations

from typing import Any

from ..queries import assignment_queries
from .responses import ok


def list_item_assignments(item_id: int, *, limit: int = 100) -> dict[str, Any]:
    return ok(assignments=assignment_queries.list_item_assignments(item_id, limit=limit))


def list_active_assignments(*, limit: int = 500) -> dict[str, Any]:
    return ok(assignments=assignment_queries.list_active_assignments(limit=limit))


def list_user_assignments(user_id: int, *, limit: int = 500) -> dict[str, Any]:
    return ok(assignments=assignment_queries.list_user_assignments(user_id, limit=limit))

from __future__ import annotations

from typing import Any

from ..queries import user_queries
from .responses import ok


def get_user(user_id: int, *, include_inactive: bool = False) -> dict[str, Any]:
    return ok(user=user_queries.get_user(user_id, include_inactive=include_inactive))


def get_by_username(username: str, *, include_inactive: bool = False) -> dict[str, Any]:
    return ok(user=user_queries.get_by_username(username, include_inactive=include_inactive))


def list_active_users(*, limit: int = 500) -> dict[str, Any]:
    return ok(users=user_queries.list_active_users(limit=limit))


def count_by_system_role(role: str) -> dict[str, Any]:
    return ok(count=user_queries.count_by_system_role(role))

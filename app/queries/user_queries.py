from __future__ import annotations

from sqlalchemy import func

from ..models import User
from .common import apply_limit


def active_users_query(*, include_inactive: bool = False):
    query = User.query
    if not include_inactive:
        query = query.filter(func.lower(User.employment_status) == "aktif")
    return query


def get_user(user_id: int | None, *, include_inactive: bool = False) -> User | None:
    if user_id is None:
        return None
    return (
        active_users_query(include_inactive=include_inactive)
        .filter(User.id == user_id)
        .first()
    )


def get_by_username(username: str | None, *, include_inactive: bool = False) -> User | None:
    value = (username or "").strip()
    if not value:
        return None
    return (
        active_users_query(include_inactive=include_inactive)
        .filter(func.lower(User.username) == value.lower())
        .first()
    )


def list_active_users(*, limit: int = 500) -> list[User]:
    query = active_users_query().order_by(User.first_name, User.last_name, User.id)
    return apply_limit(query, limit=limit).all()


def count_by_system_role(role: str) -> int:
    normalized = (role or "").strip().lower()
    if not normalized:
        return 0
    return User.query.filter(func.lower(User.system_role) == normalized).count()

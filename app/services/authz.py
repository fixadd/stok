from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from flask import session

if TYPE_CHECKING:
    from app.models import User

SYSTEM_ROLE_LEVELS = {
    "user": 0,
    "admin": 1,
    "superadmin": 2,
}


def get_active_user() -> User | None:
    from app.models import User

    user_id = session.get("active_user_id")
    if not user_id:
        return None
    user = User.query.get(user_id)
    if user is None:
        return None
    if (user.employment_status or "aktif").strip().lower() != "aktif":
        session.pop("active_user_id", None)
        return None
    return user


def set_active_user(user: User | None) -> None:
    if user is None:
        session.pop("active_user_id", None)
        return
    session["active_user_id"] = user.id


def get_system_role(user: User | None) -> str:
    if user is None:
        return "user"
    role = (user.system_role or "user").strip().lower()
    return role if role in SYSTEM_ROLE_LEVELS else "user"


def has_system_role(user: User | None, required: str) -> bool:
    required_role = (required or "").strip().lower()
    if required_role not in SYSTEM_ROLE_LEVELS:
        return False
    return SYSTEM_ROLE_LEVELS[get_system_role(user)] >= SYSTEM_ROLE_LEVELS[required_role]


def current_actor_name() -> str:
    user = get_active_user()
    if user is None:
        return "Sistem"
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.username or "Sistem"


def is_safe_redirect_target(target: str | None) -> bool:
    if not isinstance(target, str) or not target:
        return False
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == "" and target.startswith("/") and not target.startswith("/\\")

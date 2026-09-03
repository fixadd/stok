from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import jsonify

from .authz import get_active_user, has_system_role


def require_system_role(required: str, message: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Protect a route with the centralized system-role hierarchy."""

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            user = get_active_user()
            if user is None:
                return jsonify({"error": "Oturum açmanız gerekiyor."}), 401
            if not has_system_role(user, required):
                return jsonify({"error": message or f"Bu işlem için {required} yetkisi gerekir."}), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Require at least the admin role."""
    return require_system_role("admin")(view)


def superadmin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Require the superadmin role."""
    return require_system_role("superadmin")(view)


def inventory_manager_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Require the admin role for inventory-management mutations."""
    return require_system_role("admin")(view)


def can_manage(user: Any) -> bool:
    """Return whether a user may perform normal admin-level mutations."""
    return has_system_role(user, "admin")


def can_manage_system(user: Any) -> bool:
    """Return whether a user may perform super-admin operations."""
    return has_system_role(user, "superadmin")

from __future__ import annotations

from typing import Any

from flask import jsonify

from .authz import get_active_user, has_system_role


def require_role(role: str):
    """Return an HTTP 403 response when the current user lacks the role."""
    if not has_system_role(get_active_user(), role):
        return jsonify({"error": f"Bu işlem için {role} yetkisi gerekir."}), 403
    return None


def require_admin():
    return require_role("admin")


def require_superadmin():
    return require_role("superadmin")

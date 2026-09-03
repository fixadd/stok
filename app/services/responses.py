from __future__ import annotations

from typing import Any


def ok(**payload: Any) -> dict[str, Any]:
    """Legacy-compatible success response helper."""
    return {"success": True, **payload}


def error(message: str, **payload: Any) -> dict[str, Any]:
    """Legacy-compatible error response helper."""
    return {"success": False, "error": message, **payload}


def api_success(*, data: Any = None, message: str = "İşlem başarılı", **extra: Any) -> dict[str, Any]:
    """Standard API envelope for newly migrated endpoints."""
    response: dict[str, Any] = {
        "success": True,
        "data": data,
        "message": message,
    }
    response.update(extra)
    return response


def api_error(
    code: str,
    message: str,
    *,
    details: Any = None,
    status: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Standard API error envelope without breaking legacy callers."""
    error_payload: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error_payload["details"] = details

    response: dict[str, Any] = {
        "success": False,
        "error": error_payload,
    }
    if status is not None:
        response["status"] = status
    response.update(extra)
    return response

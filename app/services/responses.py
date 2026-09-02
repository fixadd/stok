from __future__ import annotations

from typing import Any


def ok(**payload: Any) -> dict[str, Any]:
    return {"success": True, **payload}


def error(message: str, **payload: Any) -> dict[str, Any]:
    return {"success": False, "error": message, **payload}

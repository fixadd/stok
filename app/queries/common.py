from __future__ import annotations

from typing import Any

from sqlalchemy import Select


def apply_limit(query: Any, *, limit: int = 500) -> Any:
    """Apply a defensive row limit to list queries without changing ordering."""
    try:
        bounded = max(1, min(int(limit), 2000))
    except (TypeError, ValueError):
        bounded = 500
    return query.limit(bounded)

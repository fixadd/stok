from __future__ import annotations

from typing import Any


def apply_limit(query: Any, *, limit: int = 500) -> Any:
    """Apply a defensive row limit when the query object supports it."""
    try:
        bounded = max(1, min(int(limit), 2000))
    except (TypeError, ValueError):
        bounded = 500
    limit_method = getattr(query, "limit", None)
    if callable(limit_method):
        return limit_method(bounded)
    return query

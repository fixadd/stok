from __future__ import annotations

from typing import Any

from flask import has_app_context
from sqlalchemy import text

from ..models import db


def load_stock_metadata_fields() -> dict[str, list[dict[str, Any]]]:
    """Load active stock form metadata from PostgreSQL.

    The schema is owned by Alembic migration 0005. An empty result is returned
    when the migration has not been applied yet, avoiding a hidden hard-coded
    schema fallback. Alembic may import application models without an active
    Flask application context, so the metadata lookup is skipped in that case.
    """
    if not has_app_context():
        return {}

    try:
        rows = db.session.execute(
            text(
                """
                SELECT category, field_key, label, placeholder,
                       required, assignment_only, options_key
                FROM stock_metadata_fields
                WHERE active = TRUE
                ORDER BY category, sort_order, id
                """
            )
        ).mappings().all()
    except Exception:
        db.session.rollback()
        return {}

    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(row["category"], []).append(
            {
                "key": row["field_key"],
                "label": row["label"],
                "placeholder": row["placeholder"] or "",
                "required": bool(row["required"]),
                "assignment_only": bool(row["assignment_only"]),
                "options_key": row["options_key"],
            }
        )
    return result


def configure_stock_metadata() -> dict[str, list[dict[str, Any]]]:
    """Return DB-backed metadata for application consumers."""
    return load_stock_metadata_fields()

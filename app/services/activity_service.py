from __future__ import annotations

from typing import Any

from ..models import ActivityLog, db

DEFAULT_EVENT_ACTOR = "Sistem"
ALLOWED_RECENT_AREAS = {
    "talep",
    "urun",
    "kullanici",
    "envanter",
    "stok",
    "bilgi",
    "profil",
    "auth",
    "sistem",
    "entegrasyon",
}


def record_activity(
    *,
    area: str,
    action: str,
    description: str | None = None,
    actor: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ActivityLog:
    """Create an activity record in the current SQLAlchemy transaction."""
    log = ActivityLog(
        area=area,
        action=action,
        description=description or None,
        actor=actor or DEFAULT_EVENT_ACTOR,
        metadata_payload=metadata or None,
    )
    db.session.add(log)
    return log


def serialize_activity_log(log: ActivityLog) -> dict[str, Any]:
    """Convert an activity model into the UI/API representation."""
    return {
        "id": log.id,
        "area": log.area,
        "action": log.action,
        "description": log.description,
        "actor": log.actor,
        "metadata": log.metadata_payload or {},
        "created_display": log.created_at.strftime("%d.%m.%Y %H:%M"),
    }


def load_activity_logs(limit: int | None = None) -> list[dict[str, Any]]:
    """Return activity records newest-first, optionally limited."""
    query = ActivityLog.query.order_by(ActivityLog.created_at.desc())
    if limit is not None:
        query = query.limit(max(0, limit))
    return [serialize_activity_log(log) for log in query.all()]


def load_recent_activity(limit: int = 6) -> list[dict[str, Any]]:
    """Return recent user-facing activity while filtering internal areas."""
    if limit <= 0:
        return []
    query_limit = max(limit * 4, limit)
    candidates = (
        ActivityLog.query.order_by(ActivityLog.created_at.desc())
        .limit(query_limit)
        .all()
    )
    filtered: list[dict[str, Any]] = []
    for log in candidates:
        if log.area not in ALLOWED_RECENT_AREAS:
            continue
        filtered.append(serialize_activity_log(log))
        if len(filtered) >= limit:
            break
    return filtered

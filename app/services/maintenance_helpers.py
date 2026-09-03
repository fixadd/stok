from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import InventoryMaintenance

MAINTENANCE_INTERVAL_DAYS = 90
MAINTENANCE_WARNING_DAYS = 15


def format_datetime_display(value: datetime | None, *, include_time: bool = True) -> str:
    if not value:
        return ""
    return value.strftime("%d.%m.%Y %H:%M" if include_time else "%d.%m.%Y")


def serialize_maintenance_record(record: InventoryMaintenance) -> dict[str, Any]:
    return {
        "id": record.id,
        "item_id": record.item_id,
        "performed_by": record.performed_by,
        "performed_at": record.performed_at.isoformat(),
        "performed_at_display": format_datetime_display(record.performed_at),
        "performed_date_display": format_datetime_display(
            record.performed_at, include_time=False
        ),
        "note": record.note or "",
        "created_at_display": format_datetime_display(record.created_at),
    }


def calculate_maintenance_status(performed_at: datetime | None) -> dict[str, Any]:
    if not performed_at:
        return {
            "status": "none",
            "label": "Bakım Yok",
            "last_maintenance_display": "Henüz bakım yapılmadı",
            "days_since_maintenance": None,
            "days_until_due": None,
        }

    today = datetime.utcnow()
    elapsed = today - performed_at
    days_since = max(0, elapsed.days)
    days_until_due = MAINTENANCE_INTERVAL_DAYS - days_since

    if days_since >= MAINTENANCE_INTERVAL_DAYS:
        status = "overdue"
        label = "Gecikmiş"
    elif days_until_due <= MAINTENANCE_WARNING_DAYS:
        status = "warning"
        label = "Yaklaşıyor"
    else:
        status = "ok"
        label = "Güncel"

    return {
        "status": status,
        "label": label,
        "last_maintenance_display": format_datetime_display(performed_at),
        "days_since_maintenance": days_since,
        "days_until_due": days_until_due,
    }


def maintenance_status_badge_class(status: str) -> str:
    if status in {"overdue", "none"}:
        return "maintenance-badge-overdue"
    if status == "warning":
        return "maintenance-badge-warning"
    return "text-bg-success-subtle text-success"


def maintenance_row_class(status: str) -> str:
    if status in {"overdue", "none"}:
        return "maintenance-row-overdue"
    if status == "warning":
        return "maintenance-row-warning"
    return ""

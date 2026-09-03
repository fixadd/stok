"""Dashboard read-model helpers."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func

from ..models import InventoryItem
from .maintenance_service import MAINTENANCE_INTERVAL_DAYS, MAINTENANCE_WARNING_DAYS, is_computer_hardware_type


def load_maintenance_metrics() -> dict[str, int]:
    """Calculate maintenance counters from each active computer's latest record."""
    items = (
        InventoryItem.query
        .filter(func.lower(InventoryItem.status).notin_(["hurda", "stokta"]))
        .all()
    )
    today = date.today()
    due = warning = overdue = current = none = 0

    for item in items:
        if not is_computer_hardware_type(item.hardware_type.name if item.hardware_type else None):
            continue
        records = sorted(item.maintenances, key=lambda row: (row.performed_at, row.id), reverse=True)
        if not records:
            none += 1
            due += 1
            continue
        next_date = (records[0].performed_at + timedelta(days=MAINTENANCE_INTERVAL_DAYS)).date()
        days_until = (next_date - today).days
        if days_until < 0:
            overdue += 1
            due += 1
        elif days_until <= MAINTENANCE_WARNING_DAYS:
            warning += 1
            due += 1
        else:
            current += 1

    return {
        "maintenance_current_count": current,
        "maintenance_warning_count": warning,
        "maintenance_overdue_count": overdue,
        "maintenance_none_count": none,
        "maintenance_due_count": due,
    }


def load_dashboard_metrics() -> dict[str, Any]:
    return load_maintenance_metrics()

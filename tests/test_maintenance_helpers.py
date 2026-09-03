from datetime import datetime, timedelta

from app.services.maintenance_helpers import (
    calculate_maintenance_status,
    format_datetime_display,
    maintenance_row_class,
    maintenance_status_badge_class,
)


def test_format_datetime_display():
    value = datetime(2026, 9, 3, 14, 5)
    assert format_datetime_display(value) == "03.09.2026 14:05"
    assert format_datetime_display(value, include_time=False) == "03.09.2026"
    assert format_datetime_display(None) == ""


def test_maintenance_status_without_history():
    payload = calculate_maintenance_status(None)
    assert payload["status"] == "none"
    assert payload["days_since_maintenance"] is None
    assert maintenance_status_badge_class("none") == "maintenance-badge-overdue"
    assert maintenance_row_class("none") == "maintenance-row-overdue"


def test_maintenance_status_warning_and_overdue():
    warning = calculate_maintenance_status(datetime.utcnow() - timedelta(days=80))
    overdue = calculate_maintenance_status(datetime.utcnow() - timedelta(days=91))

    assert warning["status"] == "warning"
    assert overdue["status"] == "overdue"
    assert maintenance_status_badge_class("warning") == "maintenance-badge-warning"
    assert maintenance_row_class("warning") == "maintenance-row-warning"

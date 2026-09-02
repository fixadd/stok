from datetime import datetime, timedelta

from app.services.maintenance_service import MAINTENANCE_WARNING_DAYS, _status


def test_maintenance_warning_window_is_inclusive():
    base = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    assert _status(base + timedelta(days=MAINTENANCE_WARNING_DAYS))["key"] == "warning"
    assert _status(base + timedelta(days=MAINTENANCE_WARNING_DAYS + 1))["key"] == "ok"


def test_maintenance_past_due_is_overdue():
    base = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    assert _status(base - timedelta(days=1))["key"] == "overdue"

from datetime import datetime

from app.services.maintenance_service import (
    MAINTENANCE_INTERVAL_DAYS,
    MAINTENANCE_WARNING_DAYS,
    _next_maintenance,
    _status,
    is_computer_hardware_type,
)


def test_computer_hardware_type_detection():
    assert is_computer_hardware_type("Dizüstü Bilgisayar")
    assert is_computer_hardware_type("HP Desktop PC")
    assert is_computer_hardware_type("Notebook")
    assert not is_computer_hardware_type("Yazıcı")
    assert not is_computer_hardware_type(None)


def test_next_maintenance_uses_configured_interval():
    performed_at = datetime(2026, 1, 1, 10, 30)
    assert _next_maintenance(performed_at) == datetime(2026, 1, 1, 10, 30).replace(day=1) + __import__("datetime").timedelta(days=MAINTENANCE_INTERVAL_DAYS)


def test_maintenance_status_warning_and_overdue_boundaries():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    assert _status(today)["key"] == "ok"
    assert _status(today.replace(day=today.day) + __import__("datetime").timedelta(days=MAINTENANCE_WARNING_DAYS))["key"] == "warning"
    assert _status(today - __import__("datetime").timedelta(days=1))["key"] == "overdue"

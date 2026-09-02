from datetime import datetime, timedelta

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
    assert _next_maintenance(performed_at) == performed_at + timedelta(days=MAINTENANCE_INTERVAL_DAYS)


def test_maintenance_status_boundaries():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    assert _status(today)["key"] == "ok"
    assert _status(today + timedelta(days=MAINTENANCE_WARNING_DAYS))["key"] == "warning"
    assert _status(today - timedelta(days=1))["key"] == "overdue"


def test_maintenance_policy_constants_are_stable():
    assert MAINTENANCE_INTERVAL_DAYS == 90
    assert MAINTENANCE_WARNING_DAYS == 15

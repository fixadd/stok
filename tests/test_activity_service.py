from datetime import datetime

from app.services.activity_service import (
    load_recent_activity,
    serialize_activity_log,
)


def test_serialize_activity_log_uses_stable_ui_shape():
    class FakeLog:
        id = 7
        area = "stok"
        action = "Stok girişi"
        description = "Laptop"
        actor = "Admin"
        metadata_payload = {"stock_item_id": 12}
        created_at = datetime(2026, 9, 3, 14, 5)

    payload = serialize_activity_log(FakeLog())

    assert payload == {
        "id": 7,
        "area": "stok",
        "action": "Stok girişi",
        "description": "Laptop",
        "actor": "Admin",
        "metadata": {"stock_item_id": 12},
        "created_display": "03.09.2026 14:05",
    }


def test_recent_activity_returns_empty_for_non_positive_limit():
    assert load_recent_activity(0) == []
    assert load_recent_activity(-1) == []

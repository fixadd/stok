from app.services.event_service import EVENT_TYPES, list_events, list_item_events, normalize_event_type


def test_event_service_delegates(monkeypatch):
    monkeypatch.setattr(
        "app.services.event_service.inventory_event_queries.list_events",
        lambda limit=500: [limit],
    )
    monkeypatch.setattr(
        "app.services.event_service.inventory_event_queries.list_item_events",
        lambda item_id, limit=100: [item_id, limit],
    )
    assert list_events(limit=20) == {"success": True, "events": [20]}
    assert list_item_events(8, limit=10) == {
        "success": True,
        "events": [8, 10],
    }


def test_event_names_are_stable_identifiers():
    assert normalize_event_type("inventory created") == "INVENTORY_CREATED"
    assert normalize_event_type("STOCK_OUT") == "STOCK_OUT"
    assert EVENT_TYPES["REPAIR_RETURNED"] == "REPAIR_RETURNED"

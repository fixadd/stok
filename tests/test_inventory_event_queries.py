from app.models import InventoryEvent
from app.queries.inventory_event_queries import (
    get_event,
    list_events,
    list_events_by_type,
    list_item_events,
)


def test_inventory_event_query_module_exposes_expected_operations():
    assert callable(get_event)
    assert callable(list_item_events)
    assert callable(list_events)
    assert callable(list_events_by_type)


def test_inventory_event_query_empty_inputs_are_safe():
    assert get_event(None) is None
    assert list_item_events(None) == []
    assert list_events_by_type("") == []


def test_inventory_event_lists_are_bounded(monkeypatch):
    class FakeQuery:
        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def first(self):
            return None

        def all(self):
            return []

        def limit(self, value):
            assert value in {100, 500}
            return self

    monkeypatch.setattr(InventoryEvent, "query", FakeQuery(), raising=False)
    assert list_item_events(1) == []
    assert list_events() == []
    assert list_events_by_type("zimmet") == []

from app.models import InventoryItem
from app.queries.inventory_queries import (
    count_by_status,
    get_by_inventory_no,
    get_item,
    list_by_factory,
    list_by_responsible_user,
    list_inventory_items,
    list_scrap_items,
)


def test_inventory_query_module_exposes_expected_operations():
    assert callable(get_item)
    assert callable(get_by_inventory_no)
    assert callable(list_by_responsible_user)
    assert callable(list_by_factory)
    assert callable(list_inventory_items)
    assert callable(list_scrap_items)
    assert callable(count_by_status)


def test_inventory_query_empty_inputs_are_safe():
    assert get_item(None) is None
    assert get_by_inventory_no("") is None
    assert list_by_responsible_user(None) == []
    assert list_by_factory(None) == []
    assert count_by_status("") == 0


def test_inventory_query_lists_are_bounded(monkeypatch):
    class FakeQuery:
        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def first(self):
            return None

        def all(self):
            return []

        def count(self):
            return 0

        def limit(self, value):
            assert value == 500
            return self

    monkeypatch.setattr(InventoryItem, "query", FakeQuery(), raising=False)
    assert list_by_responsible_user(1) == []
    assert list_by_factory(2) == []
    assert list_inventory_items() == []
    assert list_scrap_items() == []
    assert count_by_status("aktif") == 0

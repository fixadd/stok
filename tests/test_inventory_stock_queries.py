from app.models import StockAssignment, StockCategory, StockItem, StockLog, StockMovement, StockUnit
from app.queries.inventory_stock_queries import (
    get_by_reference_code,
    get_by_sku,
    get_item,
    list_categories,
    list_item_assignments,
    list_item_logs,
    list_item_movements,
    list_items,
    list_low_quantity,
    list_units,
)


def test_stock_query_module_exposes_expected_operations():
    assert callable(get_item)
    assert callable(get_by_sku)
    assert callable(get_by_reference_code)
    assert callable(list_items)
    assert callable(list_low_quantity)
    assert callable(list_item_logs)
    assert callable(list_item_movements)
    assert callable(list_item_assignments)
    assert callable(list_categories)
    assert callable(list_units)


def test_stock_query_empty_inputs_are_safe():
    assert get_item(None) is None
    assert get_by_sku("") is None
    assert get_by_reference_code("") is None
    assert list_item_logs(None) == []
    assert list_item_movements(None) == []
    assert list_item_assignments(None) == []


def test_stock_query_lists_are_bounded(monkeypatch):
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

    for model in (StockItem, StockCategory, StockUnit, StockLog, StockMovement, StockAssignment):
        monkeypatch.setattr(model, "query", FakeQuery(), raising=False)

    assert list_items() == []
    assert list_low_quantity() == []
    assert list_item_logs(1) == []
    assert list_item_movements(1) == []
    assert list_item_assignments(1) == []
    assert list_categories() == []
    assert list_units() == []

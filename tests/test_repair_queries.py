from app.queries import repair_queries


def test_get_item_delegates_to_inventory_query(monkeypatch):
    expected = object()

    class Query:
        def get(self, item_id):
            assert item_id == 123
            return expected

    monkeypatch.setattr(repair_queries.InventoryItem, "query", Query())
    assert repair_queries.get_item(123) is expected


def test_get_record_filters_by_item_and_repair(monkeypatch):
    expected = object()

    class Query:
        def filter_by(self, **kwargs):
            assert kwargs == {"id": 9, "item_id": 3}
            return self

        def first(self):
            return expected

    monkeypatch.setattr(repair_queries.InventoryRepair, "query", Query())
    assert repair_queries.get_record(3, 9) is expected


def test_list_records_filters_and_orders(monkeypatch):
    expected = [object()]

    class Query:
        def filter(self, expression):
            assert expression is not None
            return self

        def order_by(self, *expressions):
            assert len(expressions) == 2
            return self

        def all(self):
            return expected

    monkeypatch.setattr(repair_queries.InventoryRepair, "query", Query())
    assert repair_queries.list_records(7) == expected


def test_list_records_without_item_lists_all(monkeypatch):
    expected = [object()]

    class Query:
        def order_by(self, *expressions):
            assert len(expressions) == 2
            return self

        def all(self):
            return expected

    monkeypatch.setattr(repair_queries.InventoryRepair, "query", Query())
    assert repair_queries.list_records() == expected

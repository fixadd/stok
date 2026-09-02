from app.models import InventoryMaintenance
from app.queries.maintenance_extended_queries import (
    get_maintenance,
    list_by_performer,
    list_recent,
)


def test_maintenance_reporting_query_module_exposes_expected_operations():
    assert callable(get_maintenance)
    assert callable(list_by_performer)
    assert callable(list_recent)


def test_maintenance_reporting_empty_inputs_are_safe():
    assert get_maintenance(None) is None
    assert list_by_performer("") == []


def test_maintenance_reporting_lists_are_bounded(monkeypatch):
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

    monkeypatch.setattr(InventoryMaintenance, "query", FakeQuery(), raising=False)
    assert list_by_performer("Admin") == []
    assert list_recent() == []

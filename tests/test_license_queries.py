from app.models import InventoryLicense
from app.queries.license_queries import (
    get_license,
    list_item_licenses,
    list_licenses,
)


def test_license_query_module_exposes_expected_operations():
    assert callable(get_license)
    assert callable(list_item_licenses)
    assert callable(list_licenses)


def test_license_query_empty_inputs_are_safe():
    assert get_license(None) is None
    assert list_item_licenses(None) == []


def test_license_lists_are_bounded(monkeypatch):
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

    monkeypatch.setattr(InventoryLicense, "query", FakeQuery(), raising=False)
    assert list_item_licenses(1) == []
    assert list_licenses() == []
    assert list_licenses(status="aktif") == []

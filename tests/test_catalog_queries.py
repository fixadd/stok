from app.models import Brand, Factory, HardwareType
from app.queries.catalog_queries import (
    find_brand,
    find_factory,
    find_hardware_type,
    list_brands,
    list_factories,
    list_hardware_types,
)


def test_catalog_query_module_exposes_expected_operations():
    assert callable(find_factory)
    assert callable(find_hardware_type)
    assert callable(find_brand)
    assert callable(list_factories)
    assert callable(list_hardware_types)
    assert callable(list_brands)


def test_catalog_empty_name_is_safe():
    assert find_factory("") is None
    assert find_hardware_type(None) is None
    assert find_brand("   ") is None


def test_catalog_lists_are_bounded(monkeypatch):
    class FakeQuery:
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def first(self): return None
        def all(self): return []
        def limit(self, value):
            assert value == 100
            return self

    for model in (Factory, HardwareType, Brand):
        monkeypatch.setattr(model, "query", FakeQuery(), raising=False)
    assert list_factories() == []
    assert list_hardware_types() == []
    assert list_brands() == []

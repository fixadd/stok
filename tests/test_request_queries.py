from app.models import RequestGroup, RequestOrder
from app.queries.request_queries import (
    get_group,
    get_group_by_key,
    get_order,
    get_order_by_number,
    list_groups,
    list_orders,
)


def test_request_query_module_exposes_expected_operations():
    assert callable(get_group)
    assert callable(get_group_by_key)
    assert callable(list_groups)
    assert callable(get_order)
    assert callable(get_order_by_number)
    assert callable(list_orders)


def test_request_query_empty_inputs_are_safe():
    assert get_group(None) is None
    assert get_group_by_key("") is None
    assert get_order(None) is None
    assert get_order_by_number("") is None


def test_request_query_lists_are_bounded(monkeypatch):
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

    monkeypatch.setattr(RequestGroup, "query", FakeQuery(), raising=False)
    monkeypatch.setattr(RequestOrder, "query", FakeQuery(), raising=False)
    assert list_groups() == []
    assert list_orders() == []

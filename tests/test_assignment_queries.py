from app.models import InventoryAssignment
from app.queries.assignment_queries import (
    get_assignment,
    get_current_item_assignment,
    list_active_assignments,
    list_active_user_assignments,
    list_item_assignments,
    list_user_assignments,
)


def test_assignment_query_module_exposes_expected_operations():
    assert callable(get_assignment)
    assert callable(get_current_item_assignment)
    assert callable(list_item_assignments)
    assert callable(list_active_assignments)
    assert callable(list_active_user_assignments)
    assert callable(list_user_assignments)


def test_assignment_query_empty_inputs_are_safe():
    assert get_assignment(None) is None
    assert get_current_item_assignment(None) is None
    assert list_item_assignments(None) == []
    assert list_active_user_assignments(None) == []
    assert list_user_assignments(None) == []


def test_assignment_lists_are_bounded(monkeypatch):
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

    monkeypatch.setattr(InventoryAssignment, "query", FakeQuery(), raising=False)
    assert get_current_item_assignment(1) is None
    assert list_item_assignments(1) == []
    assert list_active_assignments() == []
    assert list_active_user_assignments(2) == []
    assert list_user_assignments(2) == []

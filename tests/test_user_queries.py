from app.models import User, db
from app.queries.user_queries import (
    count_by_system_role,
    get_by_username,
    get_user,
    list_active_users,
)


def test_user_query_module_exposes_expected_operations():
    assert callable(get_user)
    assert callable(get_by_username)
    assert callable(list_active_users)
    assert callable(count_by_system_role)


def test_user_query_filters_inactive_users(monkeypatch):
    class FakeQuery:
        def filter(self, *args):
            return self

        def filter_by(self, **kwargs):
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

    monkeypatch.setattr(User, "query", FakeQuery(), raising=False)
    assert get_user(None) is None
    assert get_by_username("") is None
    assert list_active_users() == []
    assert count_by_system_role("admin") == 0

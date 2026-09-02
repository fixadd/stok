from app.services import user_query_service


def test_user_query_service_exports_expected_operations():
    assert callable(user_query_service.get_user)
    assert callable(user_query_service.get_by_username)
    assert callable(user_query_service.list_active_users)
    assert callable(user_query_service.count_by_system_role)


def test_user_query_service_delegates_to_query_layer(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(
        user_query_service.user_queries,
        "get_user",
        lambda user_id, include_inactive=False: sentinel,
    )
    result = user_query_service.get_user(7)
    assert result == {"success": True, "user": sentinel}

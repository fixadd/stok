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
    monkeypatch.setattr(
        user_query_service.user_queries,
        "get_by_username",
        lambda username, include_inactive=False: username,
    )
    monkeypatch.setattr(
        user_query_service.user_queries,
        "list_active_users",
        lambda limit=500: [limit],
    )
    monkeypatch.setattr(
        user_query_service.user_queries,
        "count_by_system_role",
        lambda role: 2 if role == "admin" else 0,
    )

    assert user_query_service.get_user(7) == {"success": True, "user": sentinel}
    assert user_query_service.get_by_username("alice") == {"success": True, "user": "alice"}
    assert user_query_service.list_active_users(limit=25) == {"success": True, "users": [25]}
    assert user_query_service.count_by_system_role("admin") == {"success": True, "count": 2}

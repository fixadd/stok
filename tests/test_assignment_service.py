from app.services.assignment_service import (
    list_active_assignments,
    list_item_assignments,
    list_user_assignments,
)


def test_assignment_service_delegates(monkeypatch):
    monkeypatch.setattr(
        "app.services.assignment_service.assignment_queries.list_item_assignments",
        lambda item_id, limit=100: [item_id, limit],
    )
    monkeypatch.setattr(
        "app.services.assignment_service.assignment_queries.list_active_assignments",
        lambda limit=500: [limit],
    )
    monkeypatch.setattr(
        "app.services.assignment_service.assignment_queries.list_user_assignments",
        lambda user_id, limit=500: [user_id, limit],
    )
    assert list_item_assignments(7, limit=10) == {"success": True, "assignments": [7, 10]}
    assert list_active_assignments(limit=20) == {"success": True, "assignments": [20]}
    assert list_user_assignments(3, limit=30) == {"success": True, "assignments": [3, 30]}

from app.services.license_service import list_item_licenses, list_licenses


def test_license_service_delegates(monkeypatch):
    monkeypatch.setattr(
        "app.services.license_service.license_queries.list_licenses",
        lambda status=None, limit=500: [status, limit],
    )
    monkeypatch.setattr(
        "app.services.license_service.license_queries.list_item_licenses",
        lambda item_id, limit=100: [item_id, limit],
    )
    assert list_licenses(status="aktif", limit=10) == {
        "success": True,
        "licenses": ["aktif", 10],
    }
    assert list_item_licenses(4, limit=5) == {
        "success": True,
        "licenses": [4, 5],
    }

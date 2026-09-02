from app.services.catalog_service import load_catalog_response, load_catalogs


def test_load_catalogs_uses_bounded_loader(monkeypatch):
    calls = []

    def loader(*, limit):
        calls.append(limit)
        return []

    monkeypatch.setattr("app.services.catalog_service.CATALOGS", {"brands": loader})
    assert load_catalogs(limit=50) == {"brands": []}
    assert calls == [50]


def test_load_catalog_response_wraps_catalogs(monkeypatch):
    monkeypatch.setattr(
        "app.services.catalog_service.load_catalogs",
        lambda limit=100: {"brands": []},
    )
    assert load_catalog_response() == {"success": True, "brands": []}

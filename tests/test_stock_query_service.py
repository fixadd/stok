from app.services.stock_query_service import (
    list_categories,
    list_low_quantity,
    list_stock_items,
    list_units,
)


def test_stock_query_service_delegates(monkeypatch):
    monkeypatch.setattr(
        "app.services.stock_query_service.inventory_stock_queries.list_items",
        lambda limit=500: [limit],
    )
    monkeypatch.setattr(
        "app.services.stock_query_service.inventory_stock_queries.list_low_quantity",
        lambda threshold=0, limit=500: [threshold, limit],
    )
    monkeypatch.setattr(
        "app.services.stock_query_service.inventory_stock_queries.list_categories",
        lambda limit=100: [limit],
    )
    monkeypatch.setattr(
        "app.services.stock_query_service.inventory_stock_queries.list_units",
        lambda limit=100: [limit],
    )
    assert list_stock_items(limit=10) == {"success": True, "items": [10]}
    assert list_low_quantity(threshold=2, limit=10) == {
        "success": True,
        "items": [2, 10],
    }
    assert list_categories(limit=5) == {"success": True, "categories": [5]}
    assert list_units(limit=6) == {"success": True, "units": [6]}

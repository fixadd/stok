import importlib


def test_service_modules_import_cleanly():
    modules = [
        "app.services.catalog_service",
        "app.services.assignment_service",
        "app.services.inventory_query_service",
        "app.services.inventory_service",
        "app.services.license_service",
        "app.services.license_tracking_service",
        "app.services.event_service",
        "app.services.maintenance_query_service",
        "app.services.request_query_service",
        "app.services.request_service",
        "app.services.stock_query_service",
        "app.services.stock_service",
        "app.services.user_query_service",
    ]
    for name in modules:
        assert importlib.import_module(name) is not None

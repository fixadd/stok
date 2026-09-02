import importlib


def test_service_modules_import_cleanly():
    modules = [
        "app.services.catalog_service",
        "app.services.assignment_service",
        "app.services.license_service",
        "app.services.event_service",
        "app.services.stock_query_service",
    ]
    for name in modules:
        assert importlib.import_module(name) is not None

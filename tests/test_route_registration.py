from app.routes.inventory import register_inventory_routes
from app.routes.requests import register_request_routes
from app.routes.stock import register_stock_routes


class DummyApp:
    def __init__(self):
        self.routes = []

    def route(self, path, **kwargs):
        def decorator(fn):
            self.routes.append((path, fn.__name__))
            return fn
        return decorator


def test_stock_routes_register_expected_pages(monkeypatch):
    app = DummyApp()
    deps = {
        "get_active_user": lambda: None,
        "has_system_role": lambda *_: False,
        "load_stock_payload": lambda: {},
        "load_scrap_inventory_payload": lambda: {},
    }
    monkeypatch.setattr("app.routes.stock.render_template", lambda *args, **kwargs: "ok")
    register_stock_routes(app, deps)
    assert {path for path, _ in app.routes} == {"/stok-takip", "/hurdalar"}


def test_inventory_and_request_routes_register_expected_pages(monkeypatch):
    app = DummyApp()
    monkeypatch.setattr("app.routes.inventory.render_template", lambda *args, **kwargs: "ok")
    monkeypatch.setattr("app.routes.requests.render_template", lambda *args, **kwargs: "ok")
    register_inventory_routes(app, {
        "load_inventory_payload": lambda: {},
        "load_license_payload": lambda: {},
    })
    register_request_routes(app, {"load_request_groups": lambda: {}})
    assert {path for path, _ in app.routes} == {
        "/envanter-takip", "/lisans-takip", "/talep-takip"
    }

from flask import Flask, abort

from app.errors import register_error_handlers


def make_app():
    app = Flask(__name__)
    app.secret_key = "test"
    register_error_handlers(app)

    @app.get("/api/forbidden")
    def forbidden_route():
        abort(403)

    @app.get("/api/conflict")
    def conflict_route():
        abort(409)

    @app.get("/page")
    def page():
        abort(404)

    return app


def test_api_404_returns_json():
    with make_app().test_client() as client:
        response = client.get("/api/missing")
    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()["error"] == "Kaynak bulunamadı."


def test_api_403_returns_json():
    with make_app().test_client() as client:
        response = client.get("/api/forbidden")
    assert response.status_code == 403
    assert response.get_json()["error"] == "Bu işlem için yetkiniz yok."


def test_api_409_returns_json():
    with make_app().test_client() as client:
        response = client.get("/api/conflict")
    assert response.status_code == 409
    assert response.get_json()["error"] == "İşlem mevcut durumla çakışıyor."

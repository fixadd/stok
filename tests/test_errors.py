from flask import Flask

from app.errors import register_error_handlers


def make_app():
    app = Flask(__name__)
    app.secret_key = "test"
    register_error_handlers(app)
    return app


def test_api_404_returns_json():
    app = make_app()
    with app.test_client() as client:
        response = client.get("/api/missing")
    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()["error"] == "Kaynak bulunamadı."


def test_api_403_returns_json():
    app = make_app()
    with app.test_request_context("/api/protected"):
        from flask import abort
        with app.test_client() as client:
            response = client.get("/api/protected")
    assert response.status_code == 404

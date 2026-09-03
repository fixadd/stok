from flask import Flask, session

from app.services.security import LoginRateLimiter, configure_security


def _configured_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    configure_security(app)
    return app


def test_login_rate_limiter_blocks_after_limit():
    limiter = LoginRateLimiter(limit=2, window_seconds=60)
    assert limiter.allowed("client")
    limiter.hit("client")
    assert limiter.allowed("client")
    limiter.hit("client")
    assert not limiter.allowed("client")


def test_csrf_protection_rejects_mutation_without_token():
    app = _configured_app()

    @app.post("/mutate")
    def mutate():
        return {"ok": True}

    with app.test_client() as client:
        response = client.post("/mutate")
        assert response.status_code == 403


def test_csrf_protection_covers_all_mutating_verbs():
    app = _configured_app()

    @app.route("/mutate", methods=["POST", "PUT", "PATCH", "DELETE"])
    def mutate():
        return {"ok": True}

    with app.test_client() as client:
        for method in ("post", "put", "patch", "delete"):
            response = getattr(client, method)("/mutate")
            assert response.status_code == 403


def test_csrf_protection_accepts_session_header_token():
    app = _configured_app()

    @app.post("/mutate")
    def mutate():
        return {"ok": True}

    with app.test_client() as client:
        with client.session_transaction() as current_session:
            current_session["csrf_token"] = "known-token"
        response = client.post("/mutate", headers={"X-CSRF-Token": "known-token"})
        assert response.status_code == 200


def test_csrf_protection_accepts_json_token():
    app = _configured_app()

    @app.post("/mutate")
    def mutate():
        return {"ok": True}

    with app.test_client() as client:
        with client.session_transaction() as current_session:
            current_session["csrf_token"] = "known-token"
        response = client.post("/mutate", json={"csrf_token": "known-token"})
        assert response.status_code == 200


def test_csrf_token_is_exposed_by_context_processor():
    app = _configured_app()

    @app.get("/token")
    def token():
        return {"token": session["csrf_token"]}

    with app.test_client() as client:
        response = client.get("/token")
        assert response.status_code == 200
        assert response.json["token"]

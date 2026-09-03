from flask import Flask, session

from app.services.security import LoginRateLimiter, configure_security


def test_login_rate_limiter_blocks_after_limit():
    limiter = LoginRateLimiter(limit=2, window_seconds=60)
    assert limiter.allowed("client")
    limiter.hit("client")
    assert limiter.allowed("client")
    limiter.hit("client")
    assert not limiter.allowed("client")


def test_csrf_protection_rejects_mutation_without_token():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    configure_security(app)

    @app.post("/mutate")
    def mutate():
        return {"ok": True}

    with app.test_client() as client:
        response = client.post("/mutate")
        assert response.status_code == 403


def test_csrf_protection_accepts_session_token():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    configure_security(app)

    @app.get("/token")
    def token():
        with session:
            return {"token": session["csrf_token"]}

    @app.post("/mutate")
    def mutate():
        return {"ok": True}

    with app.test_client() as client:
        with client.session_transaction() as current_session:
            current_session["csrf_token"] = "known-token"
        response = client.post("/mutate", headers={"X-CSRF-Token": "known-token"})
        assert response.status_code == 200

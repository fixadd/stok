import pytest
from flask import Flask

from app.config import AppConfig


def configure(monkeypatch, **values):
    defaults = {
        "DATABASE_URL": "postgresql+psycopg://stok:pass@localhost/stok",
        "SECRET_KEY": "test-secret",
        "APP_ENV": "development",
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": "false",
        "SESSION_LIFETIME_MINUTES": "480",
    }
    defaults.update(values)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    app = Flask(__name__)
    AppConfig.configure(app, data_dir=None, info_upload_dir=None)
    return app


def test_configure_sets_session_security(monkeypatch):
    app = configure(monkeypatch)
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is False
    assert app.permanent_session_lifetime.total_seconds() == 480 * 60


def test_security_headers_are_added(monkeypatch):
    app = configure(monkeypatch)
    response = app.test_client().get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"


def test_non_postgresql_database_is_rejected(monkeypatch):
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        configure(monkeypatch, DATABASE_URL="sqlite:///not-allowed.db")


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://stok:pass@localhost/stok")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        AppConfig.configure(Flask(__name__), data_dir=None, info_upload_dir=None)


def test_invalid_session_lifetime_is_rejected(monkeypatch):
    with pytest.raises(RuntimeError, match="SESSION_LIFETIME_MINUTES"):
        configure(monkeypatch, SESSION_LIFETIME_MINUTES="0")


def test_samesite_none_requires_secure_cookie(monkeypatch):
    with pytest.raises(RuntimeError, match="SameSite=None"):
        configure(monkeypatch, SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE="false")

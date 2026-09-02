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
        "SESSION_LIFETIME_MINUTES": "60",
    }
    defaults.update(values)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    app = Flask(__name__)
    AppConfig.configure(app, data_dir=None, info_upload_dir=None)
    return app


def test_production_defaults_secure_cookie(monkeypatch):
    app = configure(
        monkeypatch,
        APP_ENV="production",
        SESSION_COOKIE_SECURE=None,
    )
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_invalid_samesite_value_is_rejected(monkeypatch):
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SAMESITE"):
        configure(monkeypatch, SESSION_COOKIE_SAMESITE="Invalid")


def test_samesite_none_requires_secure_cookie(monkeypatch):
    with pytest.raises(RuntimeError, match="SameSite=None"):
        configure(monkeypatch, SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE="false")


def test_invalid_lifetime_is_rejected(monkeypatch):
    with pytest.raises(RuntimeError, match="SESSION_LIFETIME_MINUTES"):
        configure(monkeypatch, SESSION_LIFETIME_MINUTES="-1")


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        configure(monkeypatch, APP_ENV="production")

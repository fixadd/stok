import pytest
from flask import Flask

from app.config import AppConfig


def test_production_defaults_secure_cookie(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://stok:pass@localhost/stok")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "strong-test-secret")
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "Lax")
    monkeypatch.setenv("SESSION_LIFETIME_MINUTES", "60")
    app = Flask(__name__)
    AppConfig.configure(app, data_dir=None, info_upload_dir=None)
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_invalid_samesite_value_is_rejected(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://stok:pass@localhost/stok")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "Invalid")
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SAMESITE"):
        AppConfig.configure(Flask(__name__), data_dir=None, info_upload_dir=None)

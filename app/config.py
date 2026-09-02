from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask


class AppConfig:
    """Central application configuration loaded from environment variables."""

    @staticmethod
    def configure(app: Flask, *, data_dir: Path, info_upload_dir: Path) -> None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL yapılandırılmamış.")

        environment = os.environ.get("APP_ENV", "development").strip().lower()
        is_production = environment in {"production", "prod"}
        secret_key = os.environ.get("SECRET_KEY", "").strip()
        if not secret_key:
            if is_production:
                raise RuntimeError("Production ortamında SECRET_KEY zorunludur.")
            secret_key = "development-only-change-me"

        try:
            session_minutes = int(os.environ.get("SESSION_LIFETIME_MINUTES", "480"))
        except ValueError as exc:
            raise RuntimeError("SESSION_LIFETIME_MINUTES sayı olmalıdır.") from exc
        if session_minutes <= 0:
            raise RuntimeError("SESSION_LIFETIME_MINUTES sıfırdan büyük olmalıdır.")

        same_site = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax").strip()
        if same_site not in {"Lax", "Strict", "None"}:
            raise RuntimeError("SESSION_COOKIE_SAMESITE Lax, Strict veya None olmalıdır.")
        if same_site == "None" and os.environ.get("SESSION_COOKIE_SECURE", "false").lower() != "true":
            raise RuntimeError("SameSite=None için SESSION_COOKIE_SECURE=true gereklidir.")

        secure_cookie = os.environ.get(
            "SESSION_COOKIE_SECURE", "true" if is_production else "false"
        ).lower() == "true"

        app.config.from_mapping(
            SECRET_KEY=secret_key,
            SQLALCHEMY_DATABASE_URI=database_url,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE=same_site,
            SESSION_COOKIE_SECURE=secure_cookie,
        )
        app.config["APP_ENV"] = environment
        app.config["DATA_DIR"] = data_dir
        app.config["INFO_UPLOAD_DIR"] = info_upload_dir

        database_path = os.environ.get("DATABASE_PATH")
        if database_path:
            resolved_database_path = Path(database_path).expanduser().resolve()
            resolved_database_path.parent.mkdir(parents=True, exist_ok=True)
            app.config["DATABASE_PATH"] = resolved_database_path
        elif database_url.startswith("sqlite:///"):
            parsed = urlparse(database_url)
            app.config["DATABASE_PATH"] = Path(parsed.path).expanduser().resolve()

        app.permanent_session_lifetime = timedelta(minutes=session_minutes)

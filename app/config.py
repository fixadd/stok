from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from flask import Flask


class AppConfig:
    """Central application configuration loaded from environment variables."""

    @staticmethod
    def configure(app: Flask, *, data_dir: Path, info_upload_dir: Path) -> None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL yapılandırılmamış.")

        secret_key = os.environ.get("SECRET_KEY")
        if not secret_key:
            if os.environ.get("APP_ENV", "development").lower() in {"production", "prod"}:
                raise RuntimeError("Production ortamında SECRET_KEY zorunludur.")
            secret_key = "development-only-change-me"

        app.config.from_mapping(
            SECRET_KEY=secret_key,
            SQLALCHEMY_DATABASE_URI=database_url,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE=os.environ.get("SESSION_COOKIE_SAMESITE", "Lax"),
            SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        )
        app.config["DATA_DIR"] = data_dir
        app.config["INFO_UPLOAD_DIR"] = info_upload_dir
        app.permanent_session_lifetime = timedelta(
            minutes=int(os.environ.get("SESSION_LIFETIME_MINUTES", "480"))
        )

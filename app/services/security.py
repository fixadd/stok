from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable

from flask import current_app, jsonify, request, session
from sqlalchemy import text


_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_CSRF_EXEMPT_ENDPOINTS = {"login", "logout", "static"}
_LOGIN_WINDOW_SECONDS = 300
_LOGIN_LIMIT = 8


class LoginRateLimiter:
    """Persistent PostgreSQL login throttle with a process-local fallback.

    Failed attempts are stored in the ``login_attempts`` table created by
    Alembic migration 0006. The in-memory limiter remains a short-lived safety
    net when the database is unavailable, so authentication is never made
    dependent on a secondary security service.
    """

    def __init__(self, limit: int = _LOGIN_LIMIT, window_seconds: int = _LOGIN_WINDOW_SECONDS) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        bucket = self._attempts[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        return bucket

    def allowed(self, key: str) -> bool:
        now = time.monotonic()
        return len(self._prune(key, now)) < self.limit

    def hit(self, key: str) -> None:
        now = time.monotonic()
        self._prune(key, now).append(now)


def _request_identity() -> tuple[str, str]:
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",", 1)[0].strip() if forwarded else request.remote_addr or "unknown"
    username = (request.form.get("username") or "").strip().casefold()
    return ip, username


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _client_key() -> str:
    ip, username = _request_identity()
    return f"{ip}:{_hash(username)[:16]}"


def _db_session():
    extension = current_app.extensions.get("sqlalchemy")
    return extension.session if extension is not None else None


def _db_allowed() -> bool | None:
    """Return DB throttle result, or None when DB tracking is unavailable."""
    ip, username = _request_identity()
    subject_hash = _hash(username)
    ip_hash = _hash(ip)
    session_obj = _db_session()
    if session_obj is None:
        return None
    try:
        row = session_obj.execute(
            text(
                """
                SELECT COUNT(*) AS failures
                FROM login_attempts
                WHERE success = FALSE
                  AND attempted_at >= CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                  AND (subject_hash = :subject_hash OR ip_hash = :ip_hash)
                """
            ),
            {"subject_hash": subject_hash, "ip_hash": ip_hash},
        ).scalar_one()
        return int(row) < _LOGIN_LIMIT
    except Exception:
        session_obj.rollback()
        return None


def record_login_attempt(success: bool) -> None:
    """Persist a login result without ever exposing the username or IP."""
    ip, username = _request_identity()
    session_obj = _db_session()
    if session_obj is not None:
        try:
            session_obj.execute(
                text(
                    """
                    INSERT INTO login_attempts (subject_hash, ip_hash, success)
                    VALUES (:subject_hash, :ip_hash, :success)
                    """
                ),
                {"subject_hash": _hash(username), "ip_hash": _hash(ip), "success": success},
            )
            session_obj.commit()
        except Exception:
            session_obj.rollback()


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _valid_csrf(provided: str | None) -> bool:
    expected = session.get("csrf_token")
    if not expected or not provided:
        return False
    return hmac.compare_digest(str(expected), str(provided))


def configure_security(app: Any) -> None:
    """Attach CSRF protection, persistent login throttling and security headers."""

    limiter = LoginRateLimiter()
    app.extensions["login_rate_limiter"] = limiter

    @app.context_processor
    def inject_security_context() -> dict[str, str]:
        return {"csrf_token": _csrf_token()}

    @app.before_request
    def enforce_csrf_and_login_rate_limit():
        endpoint = request.endpoint or ""

        if endpoint == "login" and request.method == "POST":
            db_allowed = _db_allowed()
            allowed = db_allowed if db_allowed is not None else limiter.allowed(_client_key())
            if not allowed:
                response = jsonify({"error": "Çok fazla başarısız giriş denemesi. Lütfen 5 dakika sonra tekrar deneyin."})
                response.status_code = 429
                response.headers["Retry-After"] = str(_LOGIN_WINDOW_SECONDS)
                return response

        if request.method not in _MUTATING_METHODS:
            return None
        if endpoint in _CSRF_EXEMPT_ENDPOINTS:
            return None
        if request.path.startswith("/static/"):
            return None

        provided = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not provided and request.is_json:
            payload = request.get_json(silent=True) or {}
            if isinstance(payload, dict):
                provided = payload.get("csrf_token")

        if not _valid_csrf(provided):
            return jsonify({"error": "CSRF doğrulaması başarısız."}), 403
        return None

    @app.after_request
    def record_login_result(response: Any) -> Any:
        if request.endpoint == "login" and request.method == "POST":
            success = response.status_code in {301, 302, 303, 307, 308}
            if success:
                record_login_attempt(True)
            else:
                limiter.hit(_client_key())
                record_login_attempt(False)
        return add_security_headers(response)

    def add_security_headers(response: Any) -> Any:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def csrf_protected(view: Callable[..., Any]) -> Callable[..., Any]:
    """Optional explicit decorator for high-risk endpoints."""
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        provided = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not _valid_csrf(provided):
            return jsonify({"error": "CSRF doğrulaması başarısız."}), 403
        return view(*args, **kwargs)
    return wrapped

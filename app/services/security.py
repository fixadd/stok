from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable

from flask import jsonify, request, session


_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_CSRF_EXEMPT_ENDPOINTS = {"login", "logout", "static"}


class LoginRateLimiter:
    """Small process-local login throttle.

    The application runs behind Gunicorn, so this is deliberately a safety
    net rather than an accounting system. It limits bursts per client IP and
    username and resets naturally when the worker restarts.
    """

    def __init__(self, limit: int = 8, window_seconds: int = 300) -> None:
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
        bucket = self._prune(key, now)
        bucket.append(now)



def _client_key() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",", 1)[0].strip() if forwarded else request.remote_addr or "unknown"
    username = (request.form.get("username") or "").strip().casefold()
    digest = hashlib.sha256(username.encode("utf-8")).hexdigest()[:16]
    return f"{ip}:{digest}"


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
    """Attach CSRF protection, login throttling and security context helpers."""

    limiter = LoginRateLimiter()
    app.extensions["login_rate_limiter"] = limiter

    @app.context_processor
    def inject_security_context() -> dict[str, str]:
        return {"csrf_token": _csrf_token()}

    @app.before_request
    def enforce_csrf_and_login_rate_limit():
        endpoint = request.endpoint or ""

        if endpoint == "login" and request.method == "POST":
            key = _client_key()
            if not limiter.allowed(key):
                response = jsonify({"error": "Çok fazla başarısız giriş denemesi. Lütfen 5 dakika sonra tekrar deneyin."})
                response.status_code = 429
                response.headers["Retry-After"] = "300"
                return response
            # Count the attempt before authentication. This protects against
            # password spraying even when the username does not exist.
            limiter.hit(key)

        if request.method not in _MUTATING_METHODS:
            return None
        if endpoint in _CSRF_EXEMPT_ENDPOINTS:
            return None
        if request.path.startswith("/static/"):
            return None

        provided = request.headers.get("X-CSRF-Token")
        if not provided:
            provided = request.form.get("csrf_token")
        if not provided and request.is_json:
            payload = request.get_json(silent=True) or {}
            if isinstance(payload, dict):
                provided = payload.get("csrf_token")

        if not _valid_csrf(provided):
            return jsonify({"error": "CSRF doğrulaması başarısız."}), 403
        return None

    @app.after_request
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

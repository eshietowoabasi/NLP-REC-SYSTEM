"""HTTP-level protections (spec §14).

- Origin check: state-changing API requests from another site are refused. Together
  with SameSite=Lax session cookies this is the CSRF defence for the JSON API.
- Security headers on every response (Nginx adds the same at the edge).
"""
from urllib.parse import urlsplit

from flask import current_app, request

from .errors import ApiError

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _origin_host(value):
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    return parts.netloc.lower() if parts.scheme in ("http", "https") and parts.netloc else None


def check_origin():
    if request.method not in UNSAFE_METHODS or not request.path.startswith("/api/"):
        return
    source = request.headers.get("Origin") or request.headers.get("Referer")
    if not source:
        return  # non-browser clients (CLI, scripts) send neither header
    host = _origin_host(source)
    allowed = {request.host.lower(), *(h.lower() for h in current_app.config.get("TRUSTED_ORIGINS", ()))}
    if host is None or host not in allowed:
        raise ApiError("Cross-site request refused", code="CSRF_ORIGIN_MISMATCH", status_code=403)


def add_security_headers(response):
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "same-origin")
    if request.path.startswith("/api/"):
        # API responses carry personal and unpublished data: never cache them.
        headers.setdefault("Cache-Control", "no-store")
        headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    return response


def register_security(app):
    app.before_request(check_origin)
    app.after_request(add_security_headers)

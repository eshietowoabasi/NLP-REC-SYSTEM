"""Application-wide error handlers that always answer with the JSON error envelope.

Clients only ever see a generic message for unexpected errors; the full traceback goes
to the server log.
"""

from __future__ import annotations

import logging

from flask import Flask, Response
from werkzeug.exceptions import HTTPException

from app.utils.responses import error

logger = logging.getLogger(__name__)

# Maps HTTP status codes to the stable error codes used by the frontend.
HTTP_ERROR_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


class ApiError(Exception):
    """An expected error raised from application code, rendered as the error envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


def register_error_handlers(app: Flask) -> None:
    """Attach JSON error handlers to ``app``."""

    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError) -> tuple[Response, int]:
        return error(exc.code, exc.message, exc.status, exc.details)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException) -> tuple[Response, int]:
        status = exc.code or 500
        code = HTTP_ERROR_CODES.get(status, "HTTP_ERROR")
        return error(code, exc.description or exc.name, status)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception) -> tuple[Response, int]:
        logger.exception("Unhandled error: %s", exc)
        return error("INTERNAL_ERROR", "An unexpected error occurred.", 500)

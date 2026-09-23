"""Uniform API error model (spec §12.1).

{"success": false, "error": {"code": ..., "message": ..., "details": {...}}}
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message, *, code=None, status_code=None, details=None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}


class ValidationError(ApiError):
    status_code = 422
    code = "VALIDATION_ERROR"


class NotFoundError(ApiError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(ApiError):
    status_code = 409
    code = "CONFLICT"


def error_response(code, message, status_code, details=None):
    body = {"success": False, "error": {"code": code, "message": message, "details": details or {}}}
    return jsonify(body), status_code


_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
}


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return error_response(err.code, err.message, err.status_code, err.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        code = _HTTP_CODES.get(err.code, "HTTP_ERROR")
        return error_response(code, err.description, err.code)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Unhandled error")
        return error_response("INTERNAL_ERROR", "An unexpected error occurred", 500)

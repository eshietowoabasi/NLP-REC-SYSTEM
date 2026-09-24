"""Helpers that build the standard JSON response envelopes.

Success: ``{"success": true, "data": ...}``
Error:   ``{"success": false, "error": {"code": ..., "message": ..., "details": {...}}}``
"""

from __future__ import annotations

from typing import Any

from flask import Response, jsonify


def success(data: Any = None, status: int = 200) -> tuple[Response, int]:
    """Wrap ``data`` in the success envelope."""
    return jsonify({"success": True, "data": data}), status


def error(
    code: str,
    message: str,
    status: int,
    details: dict[str, Any] | None = None,
) -> tuple[Response, int]:
    """Build the error envelope with a machine-readable ``code`` and a human message."""
    return (
        jsonify(
            {
                "success": False,
                "error": {"code": code, "message": message, "details": details or {}},
            }
        ),
        status,
    )

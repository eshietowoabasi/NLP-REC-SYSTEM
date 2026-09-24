"""Request validation with Pydantic, and pagination of list endpoints."""

from __future__ import annotations

from math import ceil
from typing import Any, TypeVar

from flask import request
from pydantic import BaseModel, ValidationError
from sqlalchemy import Select, func, select

from app.extensions import db
from app.utils.errors import ApiError

M = TypeVar("M", bound=BaseModel)

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def validation_details(exc: ValidationError) -> dict[str, list[str]]:
    """Turn Pydantic errors into ``{"field": ["message", ...]}`` for the error envelope."""
    fields: dict[str, list[str]] = {}
    for err in exc.errors():
        field = ".".join(str(part) for part in err["loc"]) or "body"
        message = str(err["msg"]).removeprefix("Value error, ")
        fields.setdefault(field, []).append(message)
    return {"fields": fields}


def parse_body(model: type[M]) -> M:
    """Validate the JSON request body against ``model`` or raise a 422 ApiError."""
    payload = request.get_json(silent=True)
    if payload is None:
        raise ApiError("BAD_REQUEST", "Request body must be a JSON object.", 400)
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ApiError(
            "VALIDATION_ERROR", "Some fields are invalid.", 422, validation_details(exc)
        ) from exc


def parse_query(model: type[M]) -> M:
    """Validate query-string parameters against ``model`` or raise a 422 ApiError."""
    try:
        return model.model_validate(request.args.to_dict())
    except ValidationError as exc:
        raise ApiError(
            "VALIDATION_ERROR", "Some query parameters are invalid.", 422, validation_details(exc)
        ) from exc


def paginate(query: Select[Any], page: int, per_page: int) -> tuple[list[Any], dict[str, int]]:
    """Run ``query`` for one page. Returns ``(items, meta)`` where meta has the page counts."""
    total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = list(db.session.scalars(query.limit(per_page).offset((page - 1) * per_page)))
    meta = {
        "page": page,
        "per_page": per_page,
        "total": total or 0,
        "pages": ceil((total or 0) / per_page) if per_page else 0,
    }
    return items, meta

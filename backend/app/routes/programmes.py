"""Academic programme management."""

from __future__ import annotations

from flask import Blueprint, Response
from sqlalchemy import select

from app.auth.decorators import login_required, role_required
from app.extensions import db
from app.models import Programme, UserRole
from app.schemas.programmes import ProgrammeCreate, ProgrammeOut
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import parse_body

bp = Blueprint("programmes", __name__, url_prefix="/programmes")


def programme_json(programme: Programme) -> dict:
    return ProgrammeOut.model_validate(programme).model_dump(mode="json")


@bp.get("")
@login_required
def list_programmes() -> tuple[Response, int]:
    programmes = db.session.scalars(
        select(Programme).where(Programme.is_active.is_(True)).order_by(Programme.name)
    ).all()
    return success([programme_json(programme) for programme in programmes])


@bp.post("")
@role_required(UserRole.ADMIN)
def create_programme() -> tuple[Response, int]:
    data = parse_body(ProgrammeCreate)
    if db.session.scalar(select(Programme).where(Programme.name.ilike(data.name))) is not None:
        raise ApiError("CONFLICT", "A programme with that name already exists.", 409)
    if data.discipline_code and db.session.scalar(
        select(Programme).where(Programme.discipline_code == data.discipline_code)
    ) is not None:
        raise ApiError("CONFLICT", "That discipline code is already in use.", 409)

    programme = Programme(**data.model_dump())
    db.session.add(programme)
    db.session.commit()
    db.session.refresh(programme)
    return success(programme_json(programme), 201)

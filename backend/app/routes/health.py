from flask import Blueprint, jsonify
from sqlalchemy import text

from ..extensions import db

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # pragma: no cover - exercised only when the DB is down
        database = "unavailable"
    status = 200 if database == "ok" else 503
    return jsonify({"success": database == "ok", "status": "ok", "database": database}), status

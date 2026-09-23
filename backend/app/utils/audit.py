from flask_login import current_user

from ..extensions import db
from ..models import AuditLog


def record_audit(action_type, entity_type=None, entity_id=None, detail=None, user_id=None, commit=True):
    """Append an AuditLog row (spec §14). Defaults to the authenticated user."""
    if user_id is None and current_user and current_user.is_authenticated:
        user_id = current_user.user_id
    entry = AuditLog(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.session.add(entry)
    if commit:
        db.session.commit()
    return entry

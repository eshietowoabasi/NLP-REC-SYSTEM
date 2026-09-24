from flask import request

from ..extensions import db
from .errors import ValidationError

MAX_PER_PAGE = 100


def paginate(query, serialize, default_per_page=20):
    """Paginate a select() using ?page= and ?per_page= and return a JSON-ready dict."""
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", default_per_page))
    except ValueError:
        raise ValidationError("page and per_page must be integers")
    if page < 1 or not 1 <= per_page <= MAX_PER_PAGE:
        raise ValidationError(f"page must be >= 1 and per_page between 1 and {MAX_PER_PAGE}")

    result = db.paginate(query, page=page, per_page=per_page, error_out=False)
    return {
        "success": True,
        "items": [serialize(item) for item in result.items],
        "pagination": {"page": page, "per_page": per_page, "total": result.total, "pages": result.pages},
    }

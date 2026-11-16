"""CSV downloads: safe cells and a UTF-8 response that spreadsheets open correctly."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from typing import Any

from flask import Response


def csv_cell(value: Any) -> str:
    """Stringify, neutralising spreadsheet formulas (CSV injection)."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def csv_response(filename: str, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> Response:
    """A CSV attachment; cells must already be safe (see :func:`csv_cell`)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        "﻿" + buffer.getvalue(),  # BOM so Excel opens the UTF-8 file correctly
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

"""Exceptions shared by the pipeline services."""

from __future__ import annotations


class AnalysisError(Exception):
    """An analysis cannot continue for a reason the planner can act on.

    ``str(exc)`` is shown to the user (e.g. "Too few passages to discover themes ...").
    """

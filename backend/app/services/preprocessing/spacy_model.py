"""spaCy pipeline loader, cached once per process (each worker loads a model only once)."""

from __future__ import annotations

from functools import lru_cache

import spacy
from spacy.language import Language


@lru_cache(maxsize=2)
def get_nlp(model_name: str = "en_core_web_sm") -> Language:
    """Load a spaCy pipeline by package name, e.g. ``en_core_web_sm``."""
    try:
        return spacy.load(model_name)
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{model_name}' is not installed. It is listed in requirements.txt; "
            "reinstall the backend dependencies."
        ) from exc

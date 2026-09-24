"""Registry of admin-configurable settings: keys, defaults and descriptions.

Values are stored in the ``settings`` table (JSON). ``flask seed`` inserts the defaults below;
:func:`get_setting` falls back to them if a row is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.extensions import db


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    default: Any
    description: str


SETTING_DEFINITIONS: tuple[SettingDefinition, ...] = (
    SettingDefinition(
        "score_weights",
        {"ner": 0.40, "topic": 0.35, "novelty": 0.25},
        "Default weights of the skill-demand, theme-strength and novelty scores (sum to 1).",
    ),
    SettingDefinition(
        "similarity_threshold",
        0.80,
        "Cosine similarity above which a candidate is flagged as a Potential Duplicate.",
    ),
    SettingDefinition(
        "max_recommendations", 20, "Maximum number of recommendations kept per session."
    ),
    SettingDefinition(
        "passage_sentences",
        {"min": 3, "max": 5},
        "Number of sentences grouped into one passage.",
    ),
    SettingDefinition(
        "passage_words",
        {"min": 100, "max": 200},
        "Target passage length in words.",
    ),
    SettingDefinition(
        "sbert_model",
        "all-MiniLM-L6-v2",
        "sentence-transformers model used for passage embeddings.",
    ),
    SettingDefinition("spacy_model", "en_core_web_sm", "spaCy pipeline used for NLP."),
    SettingDefinition("min_topic_size", 5, "BERTopic minimum topic size."),
    SettingDefinition(
        "evidence_per_recommendation",
        8,
        "Number of representative passages stored as evidence for each recommendation.",
    ),
    SettingDefinition(
        "max_documents_per_session", 50, "Maximum number of documents in one session."
    ),
    SettingDefinition(
        "credit_unit_allowance",
        None,
        "Credit units available for the institution-designed 30% (unset until configured).",
    ),
)

DEFAULT_SETTINGS: dict[str, Any] = {item.key: item.default for item in SETTING_DEFINITIONS}


def get_setting(key: str) -> Any:
    """Return the stored value of a setting, or its default if it has not been stored."""
    from app.models.configuration import Setting

    if key not in DEFAULT_SETTINGS:
        raise KeyError(f"Unknown setting '{key}'")
    row = db.session.get(Setting, key)
    return row.value if row is not None else DEFAULT_SETTINGS[key]

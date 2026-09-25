"""Skill extraction with spaCy NER plus an EntityRuler built from the admin's skill patterns.

The EntityRuler is placed before the statistical NER component, so pattern matches always win.
Only entities produced by the ruler (they carry the pattern ``id`` = canonical skill name) count
as skills; statistical entities such as ORG or GPE are ignored. Runs on the original-cased
passage text, because casing matters for patterns like "Go developer" or "R programming".
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import spacy
from spacy.language import Language

# Components not needed to find entities; excluding them makes extraction much faster.
_EXCLUDED = ["parser", "lemmatizer", "tagger", "attribute_ruler", "senter"]


@dataclass(frozen=True)
class SkillPatternSpec:
    """One active pattern: ``pattern`` is a phrase string or a spaCy token pattern list."""

    label: str
    pattern: str | list[dict[str, Any]]
    canonical_name: str


@dataclass(frozen=True)
class SkillMention:
    name: str  # canonical skill name
    label: str  # SKILL, TOOL, CERT or LANGUAGE


@dataclass
class SkillStats:
    """How often a skill appears in the corpus."""

    name: str
    label: str
    mentions: int = 0
    documents: set[int] = field(default_factory=set)
    by_category: Counter[str] = field(default_factory=Counter)

    @property
    def document_frequency(self) -> int:
        return len(self.documents)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "mentions": self.mentions,
            "document_frequency": self.document_frequency,
            "by_category": dict(self.by_category),
        }


def _key(specs: tuple[SkillPatternSpec, ...]) -> str:
    return json.dumps(
        [[s.label, s.pattern, s.canonical_name] for s in specs], sort_keys=True, default=str
    )


@lru_cache(maxsize=4)
def _build(model_name: str, key: str) -> Language:
    specs = json.loads(key)
    nlp = spacy.load(model_name, exclude=list(_EXCLUDED))
    if not specs:  # no active patterns: nothing can be a skill
        return nlp
    before = "ner" if "ner" in nlp.pipe_names else None
    ruler = nlp.add_pipe(
        "entity_ruler",
        before=before,
        config={"phrase_matcher_attr": "LOWER", "overwrite_ents": True},
    )
    ruler.add_patterns(  # type: ignore[attr-defined]
        [
            {"label": label, "pattern": pattern, "id": canonical}
            for label, pattern, canonical in specs
        ]
    )
    return nlp


def build_skill_pipeline(model_name: str, specs: list[SkillPatternSpec]) -> Language:
    """A spaCy pipeline with an EntityRuler for ``specs`` (cached per model and pattern set)."""
    return _build(model_name, _key(tuple(specs)))


def canonical_lookup(specs: list[SkillPatternSpec], nlp: Language) -> dict[str, str]:
    """Map the forms a skill can take in topic keywords to its canonical name.

    Topic keywords are lowercase lemmas with punctuation removed, so "Machine Learning" appears
    as "machine learn" and "Node.js" as "nodejs". Each phrase pattern and canonical name is
    registered in its lowercase, lemmatised and punctuation-free forms. ``nlp`` must be the
    full pipeline (with the lemmatiser), e.g. ``get_nlp("en_core_web_sm")``.
    """
    from app.services.preprocessing.normalise import StopWords, normalise_spans
    from app.services.topics.titles import stem_key

    stop_words = StopWords.build()
    lookup: dict[str, str] = {}

    def register(key: str, canonical: str) -> None:
        key = " ".join(key.split())
        stripped = re.sub(r"[^a-z0-9 ]+", "", key)
        for variant in (key, stripped, stem_key(key), stem_key(stripped)):
            if variant:
                lookup.setdefault(variant, canonical)

    phrases = {s.canonical_name: s.canonical_name for s in specs}
    phrases.update({s.pattern: s.canonical_name for s in specs if isinstance(s.pattern, str)})
    for (phrase, canonical), doc in zip(phrases.items(), nlp.pipe(phrases), strict=True):
        register(phrase.lower(), canonical)
        register(normalise_spans([doc[:]], stop_words), canonical)
    return lookup


def extract_mentions(nlp: Language, texts: list[str]) -> list[list[SkillMention]]:
    """Skill mentions per text (a skill mentioned twice in a text is listed twice)."""
    return [
        [SkillMention(ent.ent_id_, ent.label_) for ent in doc.ents if ent.ent_id_]
        for doc in nlp.pipe(texts, batch_size=64)
    ]


def aggregate_skills(
    mentions: list[list[SkillMention]], document_ids: list[int], categories: list[str]
) -> dict[str, SkillStats]:
    """Corpus-level counts per skill: mentions, distinct documents, mentions per category."""
    stats: dict[str, SkillStats] = {}
    for passage_mentions, document_id, category in zip(
        mentions, document_ids, categories, strict=True
    ):
        for mention in passage_mentions:
            skill = stats.setdefault(mention.name, SkillStats(mention.name, mention.label))
            skill.mentions += 1
            skill.documents.add(document_id)
            skill.by_category[category] += 1
    return stats


def ranked_skills(stats: dict[str, SkillStats]) -> list[SkillStats]:
    """Most demanded first: by document frequency, then mentions, then name."""
    return sorted(stats.values(), key=lambda s: (-s.document_frequency, -s.mentions, s.name))


def skills_in_passages(
    mentions: list[list[SkillMention]], indices: list[int], top_n: int = 10
) -> list[tuple[str, str, int]]:
    """The ``top_n`` most mentioned skills within the given passages: (name, label, mentions)."""
    counts: Counter[str] = Counter()
    labels: dict[str, str] = defaultdict(str)
    for index in indices:
        for mention in mentions[index]:
            counts[mention.name] += 1
            labels[mention.name] = mention.label
    return [
        (name, labels[name], count)
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n]
    ]

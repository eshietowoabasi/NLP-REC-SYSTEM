"""Readable titles and descriptions for candidate topics.

A title is built from the topic's top c-TF-IDF keywords (lowercase lemmas), e.g. keywords
``["cloud security", "kubernetes", "cloud", "docker"]`` → "Cloud Security, Kubernetes and Docker".

Rules, in order:

* keywords containing a generic job-advert word ("engineer", "team", ...) are skipped;
* a single word is replaced by a top two-word phrase containing it ("machine" → "machine learn");
* a term sharing a word stem with an already chosen term is skipped ("learning" after
  "machine learn"), so titles never repeat themselves;
* terms matching a known skill use its canonical spelling ("Machine Learning", "Node.js"),
  common acronyms are upper-cased, other words are title-cased.

Words are compared by Porter stem (NLTK; spaCy has no stemmer), because the same word appears
in different forms in different passages. Planners can edit titles afterwards; the machine
title is kept as ``auto_title``.
"""

from __future__ import annotations

from functools import lru_cache

from nltk.stem import PorterStemmer

ACRONYMS = {
    "ai": "AI", "api": "API", "apis": "APIs", "aws": "AWS", "ci": "CI", "cd": "CD",
    "css": "CSS", "gcp": "GCP", "html": "HTML", "ict": "ICT", "iot": "IoT", "it": "IT",
    "ml": "ML", "nlp": "NLP", "sql": "SQL", "ui": "UI", "ux": "UX", "nuc": "NUC",
    "rest": "REST", "soc": "SOC", "siem": "SIEM", "devops": "DevOps", "mlops": "MLOps",
}  # fmt: skip

# Frequent in job adverts and curricula (roles, generic verbs) but not a topic by themselves.
GENERIC_TERMS = frozenset(
    [
        "engineer",
        "developer",
        "analyst",
        "specialist",
        "officer",
        "manager",
        "team",
        "role",
        "staff",
        "colleague",
        "client",
        "architect",
        "tester",
        "responder",
        "designer",
        "scientist",
        "researcher",
        "administrator",
        "consultant",
        "intern",
        "graduate",
        "professional",
        "expert",
        "lead",
        "head",
        "member",
        "group",
        "squad",
        "unit",
        "build",
        "use",
        "work",
        "design",
        "develop",
        "manage",
        "support",
        "junior",
        "senior",
        "expect",
        "successful",
        "sprint",
        "quarter",
        "week",
        "month",
        "year",
        "result",
        "document",
        "student",
        "learner",
        "course",
        "cover",
        "study",
        "include",
        "introduce",
        "every",
        "each",
        "new",
        "good",
    ]
)

MAX_TITLE_TERMS = 3
MAX_TITLE_LENGTH = 255
EXCERPT_LENGTH = 240

_stemmer = PorterStemmer()


@lru_cache(maxsize=4096)
def stem(word: str) -> str:
    return _stemmer.stem(word)


def stem_key(term: str) -> str:
    """ "machine learning" and "machine learn" → "machin learn"."""
    return " ".join(stem(word) for word in term.split())


def pretty_term(term: str, canonical: dict[str, str]) -> str:
    """Display form of a keyword: canonical skill name, acronym, or title case."""
    for key in (term, stem_key(term)):
        if key in canonical:
            return canonical[key]
    return " ".join(
        canonical.get(word) or ACRONYMS.get(word) or word.capitalize() for word in term.split()
    )


def _is_generic(term: str) -> bool:
    return any(word in GENERIC_TERMS or stem(word) in _GENERIC_STEMS for word in term.split())


_GENERIC_STEMS = frozenset(stem(word) for word in GENERIC_TERMS)


def title_terms(keywords: list[str], limit: int = MAX_TITLE_TERMS) -> list[str]:
    """Up to ``limit`` distinctive keywords for a title (see the module docstring)."""
    candidates = [k for k in keywords if k and not _is_generic(k)]
    phrases = [k for k in candidates if " " in k]
    chosen: list[str] = []
    used_stems: set[str] = set()
    for keyword in candidates:
        if " " not in keyword:
            keyword = next(
                (p for p in phrases if stem(keyword) in {stem(w) for w in p.split()}), keyword
            )
        stems = {stem(word) for word in keyword.split()}
        if stems & used_stems:
            continue
        chosen.append(keyword)
        used_stems |= stems
        if len(chosen) == limit:
            break
    return chosen


def join_terms(terms: list[str]) -> str:
    if len(terms) <= 1:
        return "".join(terms)
    return f"{', '.join(terms[:-1])} and {terms[-1]}"


def merge_known_phrases(terms: list[str], canonical: dict[str, str]) -> list[str]:
    """Join two single-word terms that together form a known skill.

    "machine" and "learn" ranked separately become "machine learn" (→ "Machine Learning").
    """
    merged = list(terms)
    changed = True
    while changed:
        changed = False
        singles = [t for t in merged if " " not in t]
        for first in singles:
            for second in singles:
                if first == second:
                    continue
                phrase = f"{first} {second}"
                if phrase in canonical or stem_key(phrase) in canonical:
                    merged[merged.index(first)] = phrase
                    merged.remove(second)
                    changed = True
                    break
            if changed:
                break
    return merged


def make_title(keywords: list[str], canonical: dict[str, str]) -> str:
    # Pick a few extra terms so that merging known phrases still leaves enough for a title.
    candidates = merge_known_phrases(title_terms(keywords, MAX_TITLE_TERMS + 2), canonical)
    terms = [pretty_term(term, canonical) for term in candidates[:MAX_TITLE_TERMS]]
    return (join_terms(terms) or "Untitled theme")[:MAX_TITLE_LENGTH]


def excerpt(text: str, length: int = EXCERPT_LENGTH) -> str:
    text = " ".join(text.split())
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "…"


def make_description(
    keywords: list[str],
    canonical: dict[str, str],
    passage_count: int,
    document_count: int,
    representative_text: str,
) -> str:
    """One short paragraph: size, main terms and the most representative passage."""
    terms = [pretty_term(term, canonical) for term in title_terms(keywords, limit=6)]
    documents = "document" if document_count == 1 else "documents"
    return (
        f"A theme found in {passage_count} passages from {document_count} {documents}, "
        f"centred on {join_terms(terms) or 'no distinctive terms'}. "
        f"Most representative passage: “{excerpt(representative_text)}”"
    )

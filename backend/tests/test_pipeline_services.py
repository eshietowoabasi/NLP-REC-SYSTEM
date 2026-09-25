"""Unit tests for the pipeline services (TF-IDF, skills, overlap, scoring, titles).

All inputs are small synthetic examples.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.models.enums import OverlapStatus
from app.services.ner.skills import (
    SkillPatternSpec,
    aggregate_skills,
    build_skill_pipeline,
    extract_mentions,
    ranked_skills,
    skills_in_passages,
)
from app.services.recommendations.scoring import (
    ScoreWeights,
    WeightsError,
    composite_score,
    min_max,
    rank,
    skill_demand_raw,
    theme_strength_raw,
)
from app.services.similarity.overlap import compare_to_core, overlap_status
from app.services.tfidf.keywords import extract_keywords
from app.services.topics.modelling import centroid, representative_passages
from app.services.topics.titles import (
    excerpt,
    make_description,
    make_title,
    pretty_term,
    title_terms,
)

# ---------------------------------------------------------------------------- TF-IDF


def test_keywords_overall_and_per_category() -> None:
    texts = [
        "cloud security kubernetes",
        "cloud security docker",
        "kubernetes docker cloud",
        "payment gateway fintech",
        "payment gateway paystack",
    ]
    categories = ["job_market", "job_market", "job_market", "policy", "policy"]

    result = extract_keywords(texts, categories, top_n=5)

    overall_terms = [k["term"] for k in result["overall"]]
    assert "cloud" in overall_terms
    assert {"cloud security", "payment gateway"} & set(overall_terms)  # bigrams are scored
    policy_terms = [k["term"] for k in result["by_category"]["policy"]]
    assert policy_terms[0] in {"payment", "gateway", "payment gateway"}
    cloud = next(k for k in result["overall"] if k["term"] == "cloud")
    assert cloud["passage_count"] == 3
    assert result["passage_count"] == 5


def test_keywords_handle_empty_text() -> None:
    result = extract_keywords(["", "  "], ["job_market", "policy"])

    assert result["overall"] == [] and result["by_category"] == {}


def test_keywords_fall_back_when_filtering_removes_everything() -> None:
    # Every term appears in every passage, so max_df would remove them all.
    texts = ["python django"] * 12

    result = extract_keywords(texts, ["academic"] * 12)

    assert {k["term"] for k in result["overall"]} >= {"python", "django"}


def test_keywords_require_one_category_per_passage() -> None:
    with pytest.raises(ValueError):
        extract_keywords(["a b"], [])


# ---------------------------------------------------------------------------- skills

PATTERNS = [
    SkillPatternSpec("LANGUAGE", "python", "Python"),
    SkillPatternSpec("TOOL", "node.js", "Node.js"),
    SkillPatternSpec("TOOL", "kubernetes", "Kubernetes"),
    SkillPatternSpec("CERT", "cissp", "CISSP"),
    SkillPatternSpec("SKILL", "machine learning", "Machine Learning"),
    SkillPatternSpec(
        "LANGUAGE", [{"ORTH": "Go"}, {"LOWER": {"IN": ["developer", "programming"]}}], "Go"
    ),
]


@pytest.fixture(scope="module")
def skill_nlp():
    return build_skill_pipeline("en_core_web_sm", PATTERNS)


def test_patterns_are_matched_case_insensitively_and_mapped_to_canonical_names(skill_nlp) -> None:
    (mentions,) = extract_mentions(
        skill_nlp, ["We need PYTHON, NODE.JS and Machine Learning skills; CISSP preferred."]
    )

    assert {(m.name, m.label) for m in mentions} == {
        ("Python", "LANGUAGE"),
        ("Node.js", "TOOL"),
        ("Machine Learning", "SKILL"),
        ("CISSP", "CERT"),
    }


def test_token_patterns_need_their_context(skill_nlp) -> None:
    with_context, without = extract_mentions(
        skill_nlp, ["Hiring a Go developer in Lagos.", "Go to the office in Abuja."]
    )

    assert [m.name for m in with_context] == ["Go"]
    assert without == []  # "Go to" is not a skill; statistical entities are ignored


def test_skill_statistics_count_distinct_documents(skill_nlp) -> None:
    texts = ["Python and Kubernetes.", "Python again.", "Kubernetes only.", "Python here."]
    mentions = extract_mentions(skill_nlp, texts)

    stats = aggregate_skills(mentions, document_ids=[1, 1, 2, 3], categories=["a", "a", "b", "b"])

    assert stats["Python"].mentions == 3 and stats["Python"].document_frequency == 2
    assert stats["Kubernetes"].document_frequency == 2
    assert dict(stats["Python"].by_category) == {"a": 2, "b": 1}
    assert [s.name for s in ranked_skills(stats)] == ["Python", "Kubernetes"]
    assert skills_in_passages(mentions, [0, 1], top_n=1) == [("Python", "LANGUAGE", 2)]


def test_no_patterns_means_no_skills() -> None:
    nlp = build_skill_pipeline("en_core_web_sm", [])

    assert "entity_ruler" not in nlp.pipe_names
    assert extract_mentions(nlp, ["Python developers in Lagos"]) == [[]]


def test_skill_pipeline_is_cached(skill_nlp) -> None:
    assert build_skill_pipeline("en_core_web_sm", list(PATTERNS)) is skill_nlp


# ---------------------------------------------------------------------------- overlap


@pytest.mark.parametrize(
    ("similarity", "expected"),
    [
        (0.80, OverlapStatus.NO_SIGNIFICANT_OVERLAP),  # exactly the threshold: not a duplicate
        (0.8000001, OverlapStatus.POTENTIAL_DUPLICATE),  # just above: duplicate
        (0.79, OverlapStatus.NO_SIGNIFICANT_OVERLAP),
        (0.95, OverlapStatus.POTENTIAL_DUPLICATE),
    ],
)
def test_threshold_boundary(similarity: float, expected: OverlapStatus) -> None:
    assert overlap_status(similarity, 0.80) is expected


def _unit_vector_at_cosine(cosine: float) -> np.ndarray:
    """A 2-D unit vector whose cosine with [1, 0] is ``cosine``."""
    return np.array([cosine, math.sqrt(1 - cosine**2)], dtype=np.float32)


def test_compare_to_core_finds_the_closest_passage_and_novelty() -> None:
    candidates = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    core = np.vstack([_unit_vector_at_cosine(0.6), np.array([0.0, 1.0], dtype=np.float32)])

    first, second = compare_to_core(candidates, core, threshold=0.80)

    assert first.closest_index == 0
    assert first.max_similarity == pytest.approx(0.6, abs=1e-6)
    assert first.novelty == pytest.approx(0.4, abs=1e-6)
    assert first.status is OverlapStatus.NO_SIGNIFICANT_OVERLAP
    assert second.closest_index == 1 and second.novelty == pytest.approx(0.0, abs=1e-6)
    assert second.status is OverlapStatus.POTENTIAL_DUPLICATE


def test_compare_to_core_at_exactly_the_threshold() -> None:
    candidate = np.array([[1.0, 0.0]], dtype=np.float32)
    core = _unit_vector_at_cosine(0.80)[None, :]

    (result,) = compare_to_core(candidate, core, threshold=0.80)

    # Float rounding can land a hair either side; the status must follow the rule exactly.
    expected = overlap_status(result.max_similarity, 0.80)
    assert result.status is expected
    assert result.max_similarity == pytest.approx(0.80, abs=1e-6)


def test_novelty_is_clipped_for_opposite_vectors() -> None:
    (result,) = compare_to_core(
        np.array([[1.0, 0.0]], dtype=np.float32), np.array([[-1.0, 0.0]], dtype=np.float32), 0.8
    )

    assert result.novelty == 1.0


def test_compare_to_core_needs_core_passages() -> None:
    with pytest.raises(ValueError):
        compare_to_core(np.ones((1, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), 0.8)


def test_centroid_is_normalised_and_representatives_are_ranked() -> None:
    embeddings = np.array([[1, 0], [0.9, 0.1], [0, 1]], dtype=np.float32)
    embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)

    centre = centroid(embeddings[[0, 1]])
    ranked = representative_passages([0, 1, 2], embeddings, centre, top_n=2)

    assert np.linalg.norm(centre) == pytest.approx(1.0)
    assert [index for index, _ in ranked] == [0, 1]
    assert ranked[0][1] >= ranked[1][1]


# ---------------------------------------------------------------------------- scoring


def test_default_weights_are_valid() -> None:
    assert ScoreWeights(0.40, 0.35, 0.25).as_dict() == {"ner": 0.40, "topic": 0.35, "novelty": 0.25}


@pytest.mark.parametrize(
    "weights",
    [(0.5, 0.5, 0.5), (0.4, 0.35, 0.2), (1.2, -0.1, -0.1), (0.4, 0.35, 0.2515)],
)
def test_invalid_weights_are_rejected(weights) -> None:
    with pytest.raises(WeightsError):
        ScoreWeights(*weights)


def test_weights_within_tolerance_are_accepted() -> None:
    ScoreWeights(0.4, 0.35, 0.2505)  # sums to 1.0005, inside the ±0.001 tolerance


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], []),
        ([3.0], [1.0]),  # a single candidate
        ([2.0, 2.0, 2.0], [1.0, 1.0, 1.0]),  # all equal
        ([0.0, 5.0, 10.0], [0.0, 0.5, 1.0]),
        ([-1.0, 1.0], [0.0, 1.0]),
    ],
)
def test_min_max(values, expected) -> None:
    assert min_max(values) == pytest.approx(expected)


def test_skill_demand_uses_log1p_of_summed_document_frequency() -> None:
    assert skill_demand_raw(["Python", "AWS"], {"Python": 3, "AWS": 2}) == pytest.approx(
        math.log1p(5)
    )
    assert skill_demand_raw([], {}) == 0.0
    assert skill_demand_raw(["Unknown"], {"Python": 3}) == 0.0


def test_theme_strength() -> None:
    assert theme_strength_raw(10, 40, 0.8) == pytest.approx(0.2)
    assert theme_strength_raw(5, 0, 1.0) == 0.0


def test_composite_score_is_the_weighted_sum() -> None:
    weights = ScoreWeights(0.40, 0.35, 0.25)

    assert composite_score(1.0, 0.5, 0.2, weights) == pytest.approx(0.4 + 0.175 + 0.05)
    assert composite_score(1.0, 1.0, 1.0, weights) == pytest.approx(1.0)


def test_rank_orders_by_composite_then_tie_breaker() -> None:
    assert rank([0.5, 0.9, 0.5], tie_breakers=[1, 1, 10]) == [1, 2, 0]


# ----------------------------------------------------------------------------- titles


def test_title_uses_canonical_names_acronyms_and_skips_overlaps() -> None:
    canonical = {"node.js": "Node.js"}

    title = make_title(["cloud security", "cloud", "api", "node.js", "docker"], canonical)

    assert title == "Cloud Security, API and Node.js"


def test_titles_prefer_phrases_and_skip_generic_words() -> None:
    keywords = ["engineer", "machine", "learning", "machine learn", "learn engineer", "python"]

    # "machine" becomes the phrase; "learning" repeats its stem; role words are skipped.
    assert title_terms(keywords) == ["machine learn", "python"]


def test_canonical_lookup_covers_lemmas_and_stripped_punctuation() -> None:
    from app.services.ner.skills import canonical_lookup
    from app.services.preprocessing.spacy_model import get_nlp

    lookup = canonical_lookup(PATTERNS, get_nlp("en_core_web_sm"))

    assert pretty_term("machine learning", lookup) == "Machine Learning"
    assert pretty_term("machine learn", lookup) == "Machine Learning"  # lemma in context
    assert pretty_term("nodejs", lookup) == "Node.js"  # punctuation removed by BERTopic
    assert make_title(["machine learn", "nodejs", "cissp"], lookup) == (
        "Machine Learning, Node.js and CISSP"
    )


def test_separately_ranked_words_of_a_known_skill_are_joined() -> None:
    from app.services.ner.skills import canonical_lookup
    from app.services.preprocessing.spacy_model import get_nlp

    lookup = canonical_lookup(PATTERNS, get_nlp("en_core_web_sm"))

    assert make_title(["machine", "learn", "model", "python"], lookup) == (
        "Machine Learning, Model and Python"
    )


def test_title_terms_and_fallbacks() -> None:
    assert title_terms(["a b", "b", "c"], limit=5) == ["a b", "c"]
    assert make_title([], {}) == "Untitled theme"
    assert make_title(["python"], {}) == "Python"


def test_description_mentions_size_terms_and_excerpt() -> None:
    description = make_description(
        ["payment gateway", "fintech"],
        {},
        passage_count=12,
        document_count=1,
        representative_text="x " * 300,
    )

    assert description.startswith(
        "A theme found in 12 passages from 1 document, centred on Payment Gateway and Fintech."
    )
    assert description.endswith("…”")
    assert excerpt("short text") == "short text"

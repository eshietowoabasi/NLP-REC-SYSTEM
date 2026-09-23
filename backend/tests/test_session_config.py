import pytest

from app.schemas.session_config import DEFAULT_SESSION_CONFIG, build_session_config
from app.utils.errors import ValidationError


def test_defaults_match_specification():
    assert build_session_config() == {
        "similarity_threshold": 0.80,
        "ner_weight": 0.40,
        "topic_weight": 0.35,
        "novelty_weight": 0.25,
        "max_recommendations": 20,
    }
    assert build_session_config() is not DEFAULT_SESSION_CONFIG


def test_valid_overrides():
    cfg = build_session_config({"ner_weight": 0.5, "topic_weight": 0.3, "novelty_weight": 0.2, "max_recommendations": 10})
    assert cfg["ner_weight"] == 0.5 and cfg["max_recommendations"] == 10


def test_weights_must_sum_to_one():
    with pytest.raises(ValidationError) as exc:
        build_session_config({"ner_weight": 0.5})
    assert "weights" in exc.value.details


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"similarity_threshold": 1.5}, "similarity_threshold"),
        ({"similarity_threshold": "high"}, "similarity_threshold"),
        ({"ner_weight": True}, "ner_weight"),
        ({"ner_weight": float("nan")}, "ner_weight"),
        ({"max_recommendations": 0}, "max_recommendations"),
        ({"max_recommendations": 2.5}, "max_recommendations"),
        ({"unexpected": 1}, "unexpected"),
    ],
)
def test_invalid_values_report_field(overrides, field):
    with pytest.raises(ValidationError) as exc:
        build_session_config(overrides)
    assert field in exc.value.details


def test_non_dict_rejected():
    with pytest.raises(ValidationError):
        build_session_config([1, 2])

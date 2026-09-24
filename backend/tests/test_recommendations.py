from collections import Counter

import numpy as np
import pytest

from app.models import OverlapStatus, Role
from app.services.embeddings import HashingEmbedder
from app.services.recommendations import (
    Candidate,
    candidate_title,
    composite_score,
    ner_scores,
    rank_candidates,
    score_candidates,
    topic_scores,
)
from app.services.similarity import build_core_index, clear_cache, detect_overlap, segment_core_text
from app.services.similarity.overlap import OverlapResult

from .corpus import theme_text

DEFAULT_CONFIG = {"ner_weight": 0.40, "topic_weight": 0.35, "novelty_weight": 0.25}


# --- similarity -------------------------------------------------------------

class TestSegmentation:
    def test_keeps_titles_and_splits_long_blocks(self):
        long_block = " ".join(f"Sentence number {i} covers operating systems and compilers." for i in range(20))
        segments = segment_core_text(f"CSC 201\n\nCSC 201: Computer Programming I\n\n{long_block}")
        assert "CSC 201" not in segments  # too short to carry meaning
        assert "CSC 201: Computer Programming I" in segments
        assert all(len(s.split()) <= 60 for s in segments[1:])
        assert len(segments) > 3

    def test_repeated_segments_removed(self):
        assert segment_core_text("Data structures and algorithms\n\nData structures and algorithms") == [
            "Data structures and algorithms"
        ]


class TestOverlap:
    def setup_method(self):
        clear_cache()

    def _index(self, embedder, texts):
        return build_core_index([(i, f"hash{i}", t) for i, t in enumerate(texts, start=1)], embedder)

    def test_threshold_and_novelty(self):
        embedder = HashingEmbedder()
        index = self._index(embedder, ["Network security and penetration testing techniques"])
        vectors = embedder.encode(["Network security and penetration testing techniques", "Cloud native deployment with Kubernetes"])
        same, different = detect_overlap(vectors, index, threshold=0.80)
        assert same.status is OverlapStatus.POTENTIAL_DUPLICATE and same.max_similarity > 0.99
        assert same.novelty == pytest.approx(1 - same.max_similarity, abs=1e-4)
        assert different.status is OverlapStatus.NO_SIGNIFICANT_OVERLAP and different.novelty > 0.9
        assert same.matches[0]["document_id"] == 1

    def test_threshold_is_strictly_greater_than(self):
        index = build_core_index([], HashingEmbedder())
        index.segments = [type("S", (), {"text": "x", "document_id": 1})()]
        index.vectors = np.array([[1.0, 0.0]], dtype=np.float32)
        at = np.array([[0.8, 0.6]], dtype=np.float32)  # cosine exactly 0.80
        assert detect_overlap(at, index, 0.80)[0].status is OverlapStatus.NO_SIGNIFICANT_OVERLAP
        assert detect_overlap(at, index, 0.79)[0].status is OverlapStatus.POTENTIAL_DUPLICATE

    def test_top_matches_sorted_and_negative_similarity_floored(self):
        index = build_core_index([], HashingEmbedder())
        index.segments = [type("S", (), {"text": t, "document_id": 1})() for t in "abc"]
        index.vectors = np.array([[-1.0, 0.0], [0.0, 1.0], [0.6, 0.8]], dtype=np.float32)
        result = detect_overlap(np.array([[-1.0, 0.0]]), index, 0.8)[0]
        assert [m["text"] for m in result.matches] == ["a", "b", "c"]  # similarities 1.0, 0.0, -0.6
        assert [m["similarity"] for m in result.matches] == [1.0, 0.0, -0.6]
        result = detect_overlap(np.array([[0.0, -1.0]]), index, 0.8)[0]
        assert result.max_similarity == 0.0 and result.novelty == 1.0

    def test_empty_index_raises(self):
        with pytest.raises(ValueError):
            detect_overlap(np.ones((1, 4)), build_core_index([], HashingEmbedder()), 0.8)

    def test_core_embeddings_cached(self):
        class CountingEmbedder(HashingEmbedder):
            calls = 0

            def encode(self, texts):
                CountingEmbedder.calls += 1
                return super().encode(texts)

        embedder = CountingEmbedder()
        docs = [(1, "sha-a", "Operating systems and concurrency control")]
        build_core_index(docs, embedder)
        build_core_index(docs, embedder)
        assert CountingEmbedder.calls == 1
        build_core_index([(1, "sha-b", "Operating systems revised syllabus")], embedder)
        assert CountingEmbedder.calls == 2  # changed content invalidates the cache


# --- scoring ----------------------------------------------------------------

def make_candidate(topic_id, passages=10, docs=(1,), mentions=None, label="Cloud, Kubernetes, Docker", distinct=None):
    mentions = Counter(mentions or {})
    return Candidate(
        topic_id=topic_id, topic_label=label, embedding=np.zeros(4, dtype=np.float32),
        passage_count=passages, distinct_passages=distinct or passages, document_ids=list(docs),
        source_category_counts={"Job Market Data": passages}, keywords=["cloud", "kubernetes"],
        representative_passages=[], entity_mentions=mentions, entity_passages=Counter(mentions),
    )


def overlap(similarity, threshold=0.8):
    status = OverlapStatus.POTENTIAL_DUPLICATE if similarity > threshold else OverlapStatus.NO_SIGNIFICANT_OVERLAP
    return OverlapResult(similarity, round(1 - similarity, 4), status, [])


class TestScores:
    def test_ner_scores_log_normalised(self):
        assert ner_scores([0, 9, 99]) == [0.0, round(np.log(10) / np.log(100), 4), 1.0]
        assert ner_scores([0, 0]) == [0.0, 0.0] and ner_scores([]) == []

    def test_topic_scores_combine_size_and_spread(self):
        # Same size: a theme found in 4 documents beats one found in a single document.
        assert topic_scores([10, 10], [4, 1]) == [1.0, 0.625]
        assert topic_scores([20, 10], [2, 2]) == [1.0, 0.75]

    def test_composite_uses_configured_weights(self):
        assert composite_score(1.0, 0.0, 0.0, DEFAULT_CONFIG) == 0.4
        assert composite_score(0.82, 0.76, 0.91, DEFAULT_CONFIG) == round(0.4 * 0.82 + 0.35 * 0.76 + 0.25 * 0.91, 4)
        assert composite_score(0.5, 0.5, 0.5, {"ner_weight": 0.2, "topic_weight": 0.2, "novelty_weight": 0.6}) == 0.5

    def test_title_prefers_dominant_skills(self):
        cand = make_candidate(0, passages=10, mentions={("Cloud Computing", "SKILL"): 6, ("Kubernetes", "TOOL"): 8, ("Excel", "TOOL"): 1})
        assert candidate_title(cand) == "Cloud Computing and Kubernetes"  # skills first, then tools
        assert candidate_title(make_candidate(1, mentions={("Excel", "TOOL"): 1})) == "Cloud, Kubernetes, Docker"

    def test_score_candidates_fills_fields_and_deduplicates_titles(self):
        cands = [
            make_candidate(0, mentions={("DevOps", "SKILL"): 9}, label="Jenkins, Pipelines, Builds"),
            make_candidate(1, mentions={("DevOps", "SKILL"): 9}, label="Terraform, Ansible, Servers"),
        ]
        score_candidates(cands, [overlap(0.1), overlap(0.9)], {**DEFAULT_CONFIG})
        assert cands[0].title == "DevOps" and cands[1].title == "DevOps: Terraform, Ansible, Servers"
        assert cands[1].overlap_status is OverlapStatus.POTENTIAL_DUPLICATE
        assert cands[0].novelty_score == 0.9 and cands[0].composite_score > cands[1].composite_score
        assert "Most demanded skills and tools: DevOps" in cands[0].description

    def test_rank_puts_duplicates_last_and_limits(self):
        cands = [make_candidate(i) for i in range(4)]
        for cand, (score, dup) in zip(cands, [(0.9, True), (0.5, False), (0.7, False), (0.95, True)]):
            cand.composite_score = score
            cand.overlap_status = OverlapStatus.POTENTIAL_DUPLICATE if dup else OverlapStatus.NO_SIGNIFICANT_OVERLAP
        assert [c.topic_id for c in rank_candidates(cands, 10)] == [2, 1, 3, 0]
        assert [c.topic_id for c in rank_candidates(cands, 3)] == [2, 1, 3]


# --- API --------------------------------------------------------------------

def test_recommendations_ranked_with_evidence(client, completed_session, core_document):
    items = client.get(f"/api/sessions/{completed_session}/recommendations").json["items"]
    assert items and [r["rank"] for r in items] == list(range(1, len(items) + 1))
    assert all(0 <= r[k] <= 1 for r in items for k in ("ner_score", "topic_score", "novelty_score", "composite_score"))
    for r in items:
        assert r["novelty_score"] == pytest.approx(1 - r["max_similarity"], abs=1e-3)
        assert r["composite_score"] == pytest.approx(0.4 * r["ner_score"] + 0.35 * r["topic_score"] + 0.25 * r["novelty_score"], abs=2e-4)
        assert "evidence" not in r

    statuses = [r["overlap_status"] for r in items]
    first_dup = statuses.index("Potential Duplicate") if "Potential Duplicate" in statuses else len(statuses)
    assert "No Significant Overlap" not in statuses[first_dup:]  # novel topics first
    novel = [r for r in items if r["overlap_status"] == "No Significant Overlap"]
    assert novel == sorted(novel, key=lambda r: -r["composite_score"])

    # The core covers security, so security topics are flagged; cloud ones are novel.
    duplicates = [r for r in items if r["overlap_status"] == "Potential Duplicate"]
    assert duplicates, "security themes should overlap the security-only core"
    assert any("Cloud" in r["topic_title"] or "DevOps" in r["topic_title"] or "AWS" in r["topic_title"] for r in novel)

    detail = client.get(f"/api/recommendations/{items[0]['rec_id']}").json["recommendation"]
    evidence = detail["evidence"]
    assert {"topic_id", "keywords", "passages", "document_ids", "skills", "core_matches"} <= set(evidence)
    assert evidence["core_matches"][0]["document_title"] == core_document.title
    with_evidence = client.get(f"/api/sessions/{completed_session}/recommendations?include_evidence=1").json["items"]
    assert "evidence" in with_evidence[0]


def test_filters_and_similarity_endpoint(client, completed_session, core_document):
    dup = client.get(f"/api/sessions/{completed_session}/recommendations?overlap_status=Potential Duplicate").json["items"]
    assert dup and all(r["overlap_status"] == "Potential Duplicate" for r in dup)
    assert client.get(f"/api/sessions/{completed_session}/recommendations?overlap_status=Maybe").status_code == 422

    sim = client.get(f"/api/sessions/{completed_session}/similarity").json
    assert sim["similarity_threshold"] == 0.8 and sim["core_document_ids"] == [core_document.document_id]
    assert all(len(item["core_matches"]) >= 1 for item in sim["items"])
    assert client.get("/api/recommendations/9999").status_code == 404


def test_planner_decisions(client, db, completed_session):
    from app.models import AuditLog

    items = client.get(f"/api/sessions/{completed_session}/recommendations").json["items"]
    novel = next(r for r in items if r["overlap_status"] == "No Significant Overlap")
    dup = next(r for r in items if r["overlap_status"] == "Potential Duplicate")

    resp = client.patch(f"/api/recommendations/{novel['rec_id']}/decision", json={"decision": "Accepted", "notes": " Strong demand "})
    assert resp.status_code == 200
    assert resp.json["recommendation"]["planner_decision"] == "Accepted"
    assert resp.json["recommendation"]["planner_notes"] == "Strong demand"

    resp = client.patch(f"/api/recommendations/{dup['rec_id']}/decision", json={"decision": "Accepted"})
    assert resp.status_code == 422 and resp.json["error"]["code"] == "JUSTIFICATION_REQUIRED"
    resp = client.patch(f"/api/recommendations/{dup['rec_id']}/decision",
                        json={"decision": "Accepted", "notes": "Core covers basics; we add applied SOC practice."})
    assert resp.status_code == 200
    assert client.patch(f"/api/recommendations/{dup['rec_id']}/decision", json={"decision": "Flagged"}).status_code == 200
    # Clearing the decision keeps notes unless they are replaced.
    cleared = client.patch(f"/api/recommendations/{dup['rec_id']}/decision", json={"decision": None}).json["recommendation"]
    assert cleared["planner_decision"] is None and cleared["planner_notes"].startswith("Core covers")

    pending = client.get(f"/api/sessions/{completed_session}/recommendations?decision=pending").json["items"]
    assert novel["rec_id"] not in {r["rec_id"] for r in pending} and dup["rec_id"] in {r["rec_id"] for r in pending}
    accepted = client.get(f"/api/sessions/{completed_session}/recommendations?decision=Accepted").json["items"]
    assert [r["rec_id"] for r in accepted] == [novel["rec_id"]]

    for body in ({}, {"decision": "Maybe"}, {"decision": "Rejected", "notes": 5}):
        assert client.patch(f"/api/recommendations/{novel['rec_id']}/decision", json=body).status_code == 422
    assert db.session.query(AuditLog).filter_by(action_type="RECOMMENDATION_DECISION").count() == 4


def test_decision_permissions(client, completed_session, make_user, login):
    rec_id = client.get(f"/api/sessions/{completed_session}/recommendations").json["items"][0]["rec_id"]
    body = {"decision": "Rejected"}
    for username, role, expected in (("viewer", Role.VIEWER, 403), ("other", Role.PLANNER, 403), ("boss", Role.ADMIN, 200)):
        client.post("/api/auth/logout")
        make_user(username, role=role)
        login(username)
        assert client.get(f"/api/recommendations/{rec_id}").status_code == 200  # everyone can read
        assert client.patch(f"/api/recommendations/{rec_id}/decision", json=body).status_code == expected


def test_recommendations_not_ready(client, make_user, login):
    from app.models import AnalysisSession

    user = make_user("p2", role=Role.PLANNER)
    login("p2")
    from app.extensions import db

    session = AnalysisSession(user_id=user.user_id, session_name="pending")
    db.session.add(session)
    db.session.commit()
    for endpoint in ("recommendations", "similarity"):
        assert client.get(f"/api/sessions/{session.session_id}/{endpoint}").json["error"]["code"] == "RESULTS_NOT_READY"

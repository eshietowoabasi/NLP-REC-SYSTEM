"""A completed analysis session built directly in the database (SYNTHETIC test data).

Used by the review, report and dashboard tests, which need finished results without running
the pipeline. The stored payloads have the same shape as the real pipeline's output.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.extensions import db
from app.models import (
    AnalysisSession,
    Document,
    DocumentSession,
    NLPResult,
    NucCoreVersion,
    OverlapStatus,
    Passage,
    Recommendation,
    RecommendationEvidence,
    User,
)


@dataclass
class ReviewSession:
    session: AnalysisSession
    recommendations: list[Recommendation]
    nuc_passage: Passage
    documents: list[Document]


def make_document(owner_id: int, title: str, category: str = "job_market") -> Document:
    document = Document(
        uploaded_by_id=owner_id,
        title=title,
        original_filename=f"{title}.txt",
        stored_filename=f"{abs(hash(title)) % 10**32:032d}.txt",
        file_type="txt",
        file_size=100,
        content_hash=f"hash-{title}",
        source_category=category,
        processing_status="ready",
        page_count=2,
        word_count=640,
    )
    db.session.add(document)
    db.session.flush()
    return document


RECOMMENDATIONS = [
    ("Cloud Security and Kubernetes", OverlapStatus.NO_SIGNIFICANT_OVERLAP, 0.9),
    ("Operating Systems", OverlapStatus.POTENTIAL_DUPLICATE, 0.6),
    ("Payment Integration", OverlapStatus.NO_SIGNIFICANT_OVERLAP, 0.4),
]


def build_review_session(owner: User, session_name: str = "Synthetic review") -> ReviewSession:
    """A completed session with two documents, a NUC core and three recommendations."""
    documents = [
        make_document(owner.id, f"Synthetic cloud advert ({session_name})"),
        make_document(owner.id, f"Synthetic policy ({session_name})", "policy"),
    ]
    documents[0].title = "Synthetic cloud advert"
    documents[1].title = "Synthetic policy"
    passages = []
    for position, (document, page) in enumerate(
        [(documents[0], 1), (documents[0], 2), (documents[1], None)]
    ):
        passage = Passage(
            document_id=document.id,
            position=position,
            page_number=page,
            text=f"Synthetic evidence passage {position} about Kubernetes and cloud security.",
            normalised_text="synthetic evidence kubernetes cloud security",
        )
        db.session.add(passage)
        passages.append(passage)
    core_document = make_document(owner.id, f"Synthetic NUC core ({session_name})", "nuc_core")
    core_document.title = "Synthetic NUC core"
    nuc_passage = Passage(
        document_id=core_document.id,
        position=0,
        page_number=4,
        text="Synthetic core passage on operating systems.",
        normalised_text="synthetic core operating system",
    )
    db.session.add(nuc_passage)
    db.session.flush()
    version = NucCoreVersion(
        document_id=core_document.id,
        version_label="Synthetic core",
        is_active=True,
        uploaded_by_id=owner.id,
    )
    db.session.add(version)
    db.session.flush()

    session = AnalysisSession(
        created_by_id=owner.id,
        session_name=session_name,
        status="completed",
        current_stage="completed",
        progress_percent=100,
        nuc_core_version_id=version.id,
        parameter_config={
            "weights": {"ner": 0.4, "topic": 0.35, "novelty": 0.25},
            "similarity_threshold": 0.8,
            "max_recommendations": 20,
        },
    )
    db.session.add(session)
    db.session.flush()
    for order, document in enumerate(documents):
        db.session.add(
            DocumentSession(session_id=session.id, document_id=document.id, processing_order=order)
        )

    recommendations = []
    for rank, (title, status, composite) in enumerate(RECOMMENDATIONS, start=1):
        rec = Recommendation(
            session_id=session.id,
            rank=rank,
            topic_id=rank - 1,
            auto_title=title,
            topic_title=title,
            topic_description=f"Synthetic description of {title}.",
            keywords=[{"term": "cloud", "weight": 0.2}],
            skills=[
                {"name": "Kubernetes", "label": "TOOL", "mentions": 3, "document_frequency": 2}
            ],
            ner_score=1.0,
            topic_score=0.5,
            novelty_score=0.3,
            composite_score=composite,
            max_similarity=0.85 if status == OverlapStatus.POTENTIAL_DUPLICATE else 0.4,
            closest_nuc_passage_id=nuc_passage.id,
            overlap_status=status,
        )
        rec.evidence = [
            RecommendationEvidence(passage_id=p.id, relevance_score=0.9 - 0.1 * i)
            for i, p in enumerate(passages)
        ]
        db.session.add(rec)
        recommendations.append(rec)

    topics = [
        {
            "topic_id": rank - 1,
            "title": title,
            "keywords": [{"term": "cloud", "weight": 0.2}, {"term": "security", "weight": 0.1}],
            "size": 12 - rank,
            "document_count": 2,
            "mean_probability": 0.9,
            "strength_raw": 0.3,
            "strength": 1.0 / rank,
            "samples": [
                {"passage_id": passages[0].id, "document_id": documents[0].id, "text": "x"}
            ],
        }
        for rank, (title, _, _) in enumerate(RECOMMENDATIONS, start=1)
    ]
    candidates = [
        {
            "topic_id": rec.topic_id,
            "title": rec.auto_title,
            "max_similarity": rec.max_similarity,
            "novelty": 1 - rec.max_similarity,
            "overlap_status": str(rec.overlap_status),
            "closest_nuc_passage": {"id": nuc_passage.id, "text": nuc_passage.text},
        }
        for rec in recommendations
    ]
    db.session.add_all(
        [
            NLPResult(
                session_id=session.id,
                result_type="tfidf",
                payload={
                    "overall": [{"term": "cloud", "score": 0.3, "passage_count": 2}],
                    "by_category": {
                        "job_market": [{"term": "cloud", "score": 0.3, "passage_count": 2}],
                        "policy": [{"term": "policy", "score": 0.2, "passage_count": 1}],
                    },
                    "passage_count": 3,
                },
            ),
            NLPResult(
                session_id=session.id,
                result_type="entities",
                payload={
                    "skills": [
                        {
                            "name": "Kubernetes",
                            "label": "TOOL",
                            "mentions": 3,
                            "document_frequency": 2,
                            "by_category": {"job_market": 3},
                        }
                    ],
                    "passages_with_skills": 3,
                    "passage_count": 3,
                    "document_count": 2,
                },
            ),
            NLPResult(
                session_id=session.id,
                result_type="topics",
                payload={
                    "topic_count": len(topics),
                    "outlier_passages": 0,
                    "modelled_passages": 3,
                    "topics": topics,
                },
            ),
            NLPResult(
                session_id=session.id,
                result_type="similarity",
                payload={"threshold": 0.8, "candidates": candidates},
            ),
        ]
    )
    db.session.commit()
    return ReviewSession(session, recommendations, nuc_passage, documents)

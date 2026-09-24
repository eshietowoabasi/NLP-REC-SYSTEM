"""Pipeline performance benchmark (spec §17.5): <= 60 s for 20 documents x ~3,000 words.

Runs the real analysis pipeline (``run_analysis``) against a throw-away in-memory
database, so timings include parsing, all NLP stages, overlap, scoring and saving.
"""
import random
import time

TARGET_SECONDS = 60

_VOCABULARY = {
    "cloud": "cloud kubernetes docker aws azure deployment containers infrastructure terraform devops pipelines monitoring",
    "security": "security firewall penetration testing vulnerability incident response threat siem encryption forensics soc",
    "data": "data machine learning python models statistics analytics dashboard sql spark airflow visualisation",
    "software": "software engineering java javascript react testing agile api microservices design code review",
}
_GENERAL = "the team will work with partners to deliver reliable services for customers across the region and support staff".split()
_BOILERPLATE = ["We are an equal opportunity employer.", "Only shortlisted candidates will be contacted."]


def synthetic_corpus(documents=20, words=3000, seed=0):
    """Job-advert-like documents with distinct themes and ~10% repeated boilerplate."""
    rng = random.Random(seed)
    themes = list(_VOCABULARY)
    corpus = []
    for i in range(documents):
        vocab = _VOCABULARY[themes[i % len(themes)]].split()
        sentences, count = [], 0
        while count < words:
            if rng.random() < 0.1:
                sentence = rng.choice(_BOILERPLATE)
            else:
                chosen = rng.sample(vocab, 7) + rng.sample(_GENERAL, 7)
                rng.shuffle(chosen)
                sentence = " ".join(chosen).capitalize() + "."
            sentences.append(sentence)
            count += len(sentence.split())
        corpus.append("\n\n".join(" ".join(sentences[j:j + 4]) for j in range(0, len(sentences), 4)))
    return corpus


def benchmark(texts: list[str], core_text: str, embedding_backend: str, sbert_model: str, warm: bool = True) -> dict:
    from .. import create_app
    from ..extensions import db
    from ..models import (AnalysisSession, Document, DocumentSession, DocumentStatus, FileType, Role,
                          SessionStatus, SourceCategory, User)
    from ..services.analysis import run_analysis
    from ..tasks import warm_up

    # Always a private in-memory database: never touch the configured one.
    app = create_app("testing", {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "EMBEDDING_BACKEND": embedding_backend,
        "SBERT_MODEL": sbert_model,
    })
    if warm:
        warm_up(app)  # production workers warm up at start; exclude one-off JIT/model loading
    with app.app_context():
        db.create_all()
        user = User(username="benchmark", email="benchmark@localhost", role=Role.ADMIN, password_hash="-")
        db.session.add(user)
        db.session.flush()

        def add(text, category, title):
            doc = Document(user_id=user.user_id, title=title, file_path="-", file_type=FileType.TXT,
                           source_category=category, processing_status=DocumentStatus.PARSED,
                           extracted_text=text, content_hash=f"bench-{title}")
            db.session.add(doc)
            db.session.flush()
            return doc

        add(core_text, SourceCategory.NUC_CORE, "core")
        session = AnalysisSession(user_id=user.user_id, session_name="benchmark", status=SessionStatus.PROCESSING,
                                  parameter_config={"similarity_threshold": 0.8, "ner_weight": 0.4, "topic_weight": 0.35,
                                                    "novelty_weight": 0.25, "max_recommendations": 20})
        for i, text in enumerate(texts):
            doc = add(text, SourceCategory.JOB_MARKET, f"doc{i}")
            session.document_links.append(DocumentSession(document_id=doc.document_id, processing_order=i))
        db.session.add(session)
        db.session.commit()

        started = time.perf_counter()
        run_analysis(session.session_id)
        wall = time.perf_counter() - started
        session = db.session.get(AnalysisSession, session.session_id)
        if session.status is not SessionStatus.COMPLETED:
            raise RuntimeError(f"Benchmark run failed: {session.error_message}")
        info = session.pipeline_info
        db.session.remove()
        db.engine.dispose()
    return {
        "documents": len(texts),
        "words": sum(len(t.split()) for t in texts),
        "wall_seconds": round(wall, 2),
        "target_seconds": TARGET_SECONDS,
        "meets_target": wall <= TARGET_SECONDS,
        "stage_seconds": info["stage_seconds"],
        "passages": info["passage_count"],
        "topics": info["topic_count"],
        "recommendations": info["recommendation_count"],
        "embedding_backend": info["embedding_backend"],
        "embedding_model": info["embedding_model"],
        "warnings": info["warnings"],
    }

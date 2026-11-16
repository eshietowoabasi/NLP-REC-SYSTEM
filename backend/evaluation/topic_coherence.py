"""Topic quality: BERTopic (as used by the system) versus an LDA baseline, by C_v coherence.

    python -m evaluation.topic_coherence --session 10 [--top-words 10] [--lda-runs 3]

Both models are scored on the same texts: the session's non-NUC passages, normalised as for
TF-IDF (lemmas, stop words removed, including the admin's domain stop words). BERTopic's topic
words are the c-TF-IDF keywords stored with the session; LDA (Gensim) is trained with the same
number of topics as BERTopic found, averaged over ``--lda-runs`` seeds. C_v (Röder, Both &
Hinneburg, 2015) is computed with Gensim's CoherenceModel over a 110-token sliding window;
UMass is reported as a second, corpus-internal measure. Gensim is used here only, never in the
application.
"""

from __future__ import annotations

import argparse
import statistics
import time

from sqlalchemy import select

from app.extensions import db
from app.models import NLPResultType, StopWord
from app.services.analysis import without_stop_words
from app.tasks.analysis import load_corpus
from evaluation.common import (
    app_context,
    completed_session,
    results_path,
    stamp,
    stored_result,
    write_json,
)


def tokenised_passages(session_id: int) -> tuple[list[list[str]], list[list[str]]]:
    """Normalised tokens of the session's passages, and BERTopic's stored topic words."""
    with app_context():
        session = completed_session(session_id)
        corpus = load_corpus(session)
        stop_words = frozenset(
            db.session.scalars(select(StopWord.word).where(StopWord.is_active.is_(True)))
        )
        topics = stored_result(session_id, NLPResultType.TOPICS).get("topics", [])
    texts = [without_stop_words(p.normalised_text, stop_words).split() for p in corpus]
    # Multi-word keywords ("machine learning") are split into their words, as C_v scores words.
    topic_words = []
    for topic in topics:
        words: list[str] = []
        for keyword in topic["keywords"]:
            for word in keyword["term"].split():
                if word not in words:
                    words.append(word)
        topic_words.append(words)
    return texts, topic_words


def coherence(topics: list[list[str]], texts: list[list[str]], dictionary, measure: str) -> float:
    from gensim.models.coherencemodel import CoherenceModel

    known = [[w for w in topic if w in dictionary.token2id] for topic in topics]
    known = [topic for topic in known if len(topic) >= 2]
    model = CoherenceModel(
        topics=known, texts=texts, dictionary=dictionary, coherence=measure, processes=1
    )
    return float(model.get_coherence())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--top-words", type=int, default=10)
    parser.add_argument("--lda-runs", type=int, default=3)
    args = parser.parse_args()

    from gensim.corpora import Dictionary
    from gensim.models import LdaModel

    texts, bertopic_topics = tokenised_passages(args.session)
    texts = [t for t in texts if t]
    bertopic_topics = [t[: args.top_words] for t in bertopic_topics]
    dictionary = Dictionary(texts)
    bow = [dictionary.doc2bow(t) for t in texts]
    k = len(bertopic_topics)
    print(f"{len(texts)} passages, {len(dictionary)} distinct tokens, {k} topics")

    result: dict = {
        "session": args.session,
        "passages": len(texts),
        "vocabulary": len(dictionary),
        "topics": k,
        "top_words": args.top_words,
        "bertopic": {
            "c_v": coherence(bertopic_topics, texts, dictionary, "c_v"),
            "u_mass": coherence(bertopic_topics, texts, dictionary, "u_mass"),
            "topic_words": bertopic_topics,
        },
        "lda": {"runs": []},
    }
    for seed in range(42, 42 + args.lda_runs):
        started = time.perf_counter()
        lda = LdaModel(
            corpus=bow,
            id2word=dictionary,
            num_topics=k,
            random_state=seed,
            passes=20,
            iterations=400,
            alpha="auto",
            eta="auto",
        )
        words = [[w for w, _ in lda.show_topic(i, topn=args.top_words)] for i in range(k)]
        result["lda"]["runs"].append(
            {
                "seed": seed,
                "c_v": coherence(words, texts, dictionary, "c_v"),
                "u_mass": coherence(words, texts, dictionary, "u_mass"),
                "seconds": round(time.perf_counter() - started, 1),
                "topic_words": words,
            }
        )
    runs = result["lda"]["runs"]
    for measure in ("c_v", "u_mass"):
        values = [r[measure] for r in runs]
        result["lda"][f"{measure}_mean"] = statistics.fmean(values)
        result["lda"][f"{measure}_sd"] = statistics.stdev(values) if len(values) > 1 else 0.0

    out = write_json(results_path(f"topic_coherence_session{args.session}_{stamp()}.json"), result)
    print(
        f"C_v   BERTopic {result['bertopic']['c_v']:.3f}   LDA {result['lda']['c_v_mean']:.3f} "
        f"± {result['lda']['c_v_sd']:.3f} ({len(runs)} runs)\n"
        f"UMass BERTopic {result['bertopic']['u_mass']:.3f}   "
        f"LDA {result['lda']['u_mass_mean']:.3f}"
        f"\nSaved → {out}"
    )


if __name__ == "__main__":
    main()

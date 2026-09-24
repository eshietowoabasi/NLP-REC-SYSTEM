import numpy as np
import pytest

from app.services.embeddings import HashingEmbedder, get_embedder, mean_embedding
from app.services.embeddings.backends import EmbeddingUnavailableError, SentenceTransformerEmbedder
from app.services.ner import aggregate_skill_demand, extract_entities
from app.services.tfidf import extract_keywords
from app.services.topics import Passage, make_label, model_topics, select_passages

from .corpus import THEMES


class TestTfidf:
    def test_distinctive_terms_rank_first(self):
        docs = [
            ["cloud", "kubernetes", "docker", "engineer", "cloud"],
            ["security", "firewall", "threat", "engineer"],
            ["data", "python", "model", "engineer"],
        ]
        result = extract_keywords(docs, top_n=3)
        assert result.per_document[0][0]["term"] == "cloud"
        assert all(k["term"] != "engineer" for k in result.per_document[1][:1])
        assert {"term", "score"} == set(result.per_document[0][0])

    def test_bigrams_and_corpus_document_frequency(self):
        docs = [["machine", "learning", "python"], ["machine", "learning", "sql"]]
        result = extract_keywords(docs)
        terms = {k["term"]: k for k in result.corpus}
        assert "machine learning" in terms
        assert terms["machine learning"]["document_frequency"] == 2

    def test_boilerplate_dropped_with_many_documents(self):
        docs = [["experience", f"topic{i}", f"skill{i}"] for i in range(6)]
        result = extract_keywords(docs)
        assert "experience" not in {k["term"] for k in result.corpus}

    def test_empty_documents(self):
        result = extract_keywords([[], ["python"], []])
        assert result.per_document[0] == [] and result.per_document[1][0]["term"] == "python"
        assert extract_keywords([[]]).corpus == []


class TestNer:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("C++ and C# developers wanted", {("C++", "TOOL"), ("C#", "TOOL")}),
            ("We use Node.js, Vue.js and .NET Core", {("Node.js", "TOOL"), ("Vue.js", "TOOL"), (".NET", "TOOL")}),
            ("Build CI/CD pipelines", {("CI/CD", "SKILL")}),
            ("AWS Certified Solutions Architect preferred", {("AWS Certified", "CERT")}),
            ("CompTIA Security+ holder", {("CompTIA Security+", "CERT")}),
            ("Power BI, TensorFlow/PyTorch", {("Power BI", "TOOL"), ("TensorFlow", "TOOL"), ("PyTorch", "TOOL")}),
            ("Experience with Go programming and R language", {("Go", "TOOL"), ("R", "TOOL")}),
            ("Machine learning and Deep Learning", {("Machine Learning", "SKILL"), ("Deep Learning", "SKILL")}),
        ],
    )
    def test_custom_patterns(self, text, expected):
        found = {(e["text"], e["label"]) for e in extract_entities([text]).custom()}
        assert found == expected

    @pytest.mark.parametrize(
        "text",
        ["We go to the market", "a spark of genius", "excel at work", "The node of the tree", "Say ai softly", "(c) section"],
    )
    def test_ordinary_words_do_not_match(self, text):
        assert extract_entities([text]).custom() == []

    def test_counts_and_standard_entities(self):
        result = extract_entities(["Python and python again.", "Jobs in Lagos use Python."])
        by_name = {(e["text"], e["label"]): e["count"] for e in result.entities}
        assert by_name[("Python", "TOOL")] == 2  # "python" lowercase is not the language
        assert ("Lagos", "GPE") in by_name
        assert result.entities[0]["label"] in ("SKILL", "TOOL", "CERT")

    def test_skill_demand_aggregation(self):
        per_doc = {
            1: extract_entities(["Python and Docker.", "Python again."]),
            2: extract_entities(["Python for data analysis in Lagos."]),
        }
        demand = {r["text"]: r for r in aggregate_skill_demand(per_doc)}
        assert demand["Python"]["mentions"] == 3 and demand["Python"]["document_frequency"] == 2
        assert demand["Python"]["document_ids"] == [1, 2]
        assert "Lagos" not in demand  # only SKILL/TOOL/CERT count as demand
        assert list(demand)[0] == "Python"  # ranked by document frequency


class TestEmbeddings:
    def test_hashing_is_deterministic_normalised_and_lexical(self):
        embedder = HashingEmbedder()
        vectors = embedder.encode(["cloud security engineer", "cloud security analyst", "poetry and literature"])
        assert vectors.shape == (3, embedder.dimension) and vectors.dtype == np.float32
        assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
        assert vectors[0] @ vectors[1] > vectors[0] @ vectors[2]
        assert np.array_equal(vectors, HashingEmbedder().encode(["cloud security engineer", "cloud security analyst", "poetry and literature"]))

    def test_empty_input_and_mean(self):
        embedder = HashingEmbedder(dimension=8)
        assert embedder.encode([]).shape == (0, 8)
        assert mean_embedding(np.zeros((0, 8))) is None
        mean = mean_embedding(embedder.encode(["cloud security", "cloud computing"]))
        assert mean.shape == (8,) and np.isclose(np.linalg.norm(mean), 1.0, atol=1e-5)

    def test_get_embedder(self):
        assert get_embedder("hashing") is get_embedder("hashing")
        assert isinstance(get_embedder("sbert", "x/y"), SentenceTransformerEmbedder)
        with pytest.raises(ValueError):
            get_embedder("word2vec")

    def test_sbert_unavailable_raises_clear_error(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(EmbeddingUnavailableError, match="EMBEDDING_BACKEND=hashing"):
            SentenceTransformerEmbedder("any/model").encode(["x"])


class TestTopics:
    def test_label(self):
        assert make_label(["cloud", "cloud security", "kubernetes", "docker"]) == "Cloud, Kubernetes, Docker"
        assert make_label([]) == "Untitled topic"

    def test_label_keeps_source_spelling(self):
        from app.services.topics.modeling import surface_forms

        forms = surface_forms(["Holders of CISSP use PyTorch", "cissp and PyTorch skills", "CISSP exam"])
        assert forms["cissp"] == "CISSP" and forms["pytorch"] == "PyTorch"
        assert make_label(["cissp", "pytorch", "skills"], forms=forms) == "CISSP, PyTorch, Skills"

    def test_select_passages_filters_short_sentences(self):
        passages = select_passages(["Too short.", "This sentence is long enough to keep."], 3, "Job Market Data")
        assert [p.text for p in passages] == ["This sentence is long enough to keep."]
        assert passages[0].document_id == 3

    def test_too_few_passages_skipped(self):
        result = model_topics([Passage("one two three four five six", 1, "x")] * 5, np.ones((5, 4), dtype=np.float32))
        assert result.method == "skipped" and result.topics == [] and result.warnings

    def test_recovers_themes(self):
        import random

        rng = random.Random(3)
        passages = []
        for doc_id, sentences in enumerate(THEMES.values(), start=1):
            words = " ".join(sentences).lower().replace(".", "").replace(",", "").split()
            for _ in range(40):
                passages.append(Passage(" ".join(rng.sample(words, 10)), doc_id, "Job Market Data"))
        vectors = HashingEmbedder().encode([p.text for p in passages])
        result = model_topics(passages, vectors)

        assert result.method == "bertopic" and len(result.topics) >= 3
        # Each large topic should be dominated by one source document (one theme).
        for topic in result.topics[:3]:
            counts = [c["passages"] for c in topic["document_counts"]]
            assert counts[0] / sum(counts) >= 0.8  # sorted, dominant document first
            assert len(topic["representative_passages"]) == 3
            assert 0 < topic["relevance"] <= 1
            assert len(topic["embedding"]) == vectors.shape[1]
        assert result.topics[0]["relevance"] == 1.0
        shares = result.document_topics[1]
        assert sum(s["passages"] for s in shares) <= 40
        assert 0 < sum(s["share"] for s in shares) <= 1.0001


class _FakeSentenceTransformer:
    """Mimics the sentence-transformers >= 6 API surface we rely on."""

    def __init__(self):
        self.calls = []

    def get_embedding_dimension(self):
        return 3

    def encode(self, texts, **kwargs):
        self.calls.append(kwargs)
        return np.array([[3.0, 4.0, 0.0] for _ in texts])


def test_sbert_embedder_uses_model_api():
    embedder = SentenceTransformerEmbedder("fake/model", batch_size=8)
    embedder._model = _FakeSentenceTransformer()
    vectors = embedder.encode(["a", "b"])
    assert vectors.shape == (2, 3) and np.allclose(vectors[0], [0.6, 0.8, 0.0])
    assert embedder.dimension == 3
    assert embedder.encode([]).shape == (0, 3)
    assert embedder._model.calls[0] == {
        "batch_size": 8, "show_progress_bar": False, "convert_to_numpy": True, "normalize_embeddings": True
    }


def test_duplicate_passages_counted_but_fitted_once():
    import random

    rng = random.Random(5)
    passages = []
    for doc_id, sentences in enumerate(THEMES.values(), start=1):
        words = " ".join(sentences).lower().replace(".", "").replace(",", "").split()
        for _ in range(30):
            passages.append(Passage(" ".join(rng.sample(words, 10)), doc_id, "Job Market Data"))
    boilerplate = "We are an equal opportunity employer and value diversity at every level"
    passages += [Passage(boilerplate, 1 + i % 3, "Job Market Data") for i in range(60)]
    result = model_topics(passages, HashingEmbedder().encode([p.text for p in passages]))

    assert result.passage_count == len(passages)
    for topic in result.topics:
        texts = [p["text"] for p in topic["representative_passages"]]
        assert len(texts) == len(set(texts))  # no repeated representative passage
        assert topic["distinct_passages"] <= topic["size"]
    # All 60 copies share one topic assignment (or are all outliers).
    counted = sum(t["size"] for t in result.topics) + result.outlier_count
    assert counted == len(passages)

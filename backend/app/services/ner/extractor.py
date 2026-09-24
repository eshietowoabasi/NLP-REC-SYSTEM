"""spaCy NER with custom Computing patterns and skill-demand aggregation (spec §8.3)."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

from ..preprocessing.pipeline import DEFAULT_SPACY_MODEL
from .patterns import build_patterns

CUSTOM_LABELS = ("SKILL", "TOOL", "CERT")
# Standard spaCy labels kept as context (employers, products, regions for localisation).
STANDARD_LABELS = ("ORG", "PRODUCT", "GPE")
KEPT_LABELS = set(CUSTOM_LABELS + STANDARD_LABELS)
_MAX_STANDARD_ENTITIES = 50


@lru_cache(maxsize=2)
def load_ner_nlp(model_name: str = DEFAULT_SPACY_MODEL):
    import spacy

    # Sentences are already split and lemmas are not needed: keep only tok2vec + ner.
    nlp = spacy.load(model_name, disable=["parser", "tagger", "attribute_ruler", "lemmatizer", "senter"])
    ruler = nlp.add_pipe(
        "entity_ruler", before="ner", config={"phrase_matcher_attr": "LOWER", "overwrite_ents": True}
    )
    ruler.add_patterns(build_patterns(nlp.tokenizer))
    return nlp


@dataclass
class DocumentEntities:
    entities: list[dict]  # [{"text", "label", "count"}], custom labels first, by count
    # SKILL/TOOL/CERT (name, label) pairs found in each input sentence, aligned with the input.
    sentence_entities: list[list[tuple[str, str]]] = field(default_factory=list)

    def custom(self):
        return [e for e in self.entities if e["label"] in CUSTOM_LABELS]


def extract_entities(sentences: list[str], model_name: str = DEFAULT_SPACY_MODEL) -> DocumentEntities:
    nlp = load_ner_nlp(model_name)
    counts = Counter()
    per_sentence = []
    for doc in nlp.pipe(sentences, batch_size=128):
        found = []
        for ent in doc.ents:
            if ent.label_ not in KEPT_LABELS:
                continue
            name = ent.ent_id_ or " ".join(ent.text.split())
            counts[(name, ent.label_)] += 1
            if ent.label_ in CUSTOM_LABELS:
                found.append((name, ent.label_))
        per_sentence.append(found)

    custom = [(k, n) for k, n in counts.items() if k[1] in CUSTOM_LABELS]
    standard = [(k, n) for k, n in counts.items() if k[1] not in CUSTOM_LABELS]
    ordered = sorted(custom, key=lambda kv: (-kv[1], kv[0])) + sorted(standard, key=lambda kv: (-kv[1], kv[0]))[:_MAX_STANDARD_ENTITIES]
    return DocumentEntities(
        [{"text": name, "label": label, "count": n} for (name, label), n in ordered], per_sentence
    )


def aggregate_skill_demand(per_document: dict[int, DocumentEntities]) -> list[dict]:
    """Corpus-level demand for SKILL/TOOL/CERT entities.

    ``mentions`` is the total count; ``document_frequency`` is how many documents mention
    it, which resists one long document dominating. Recommendation scoring (Sprint 4)
    normalises these to 0–1 (docs/DECISIONS.md, D4).
    """
    mentions = Counter()
    documents = defaultdict(set)
    for document_id, result in per_document.items():
        for entity in result.custom():
            key = (entity["text"], entity["label"])
            mentions[key] += entity["count"]
            documents[key].add(document_id)
    rows = [
        {
            "text": name,
            "label": label,
            "mentions": n,
            "document_frequency": len(documents[(name, label)]),
            "document_ids": sorted(documents[(name, label)]),
        }
        for (name, label), n in mentions.items()
    ]
    return sorted(rows, key=lambda r: (-r["document_frequency"], -r["mentions"], r["text"]))


def entity_spans(texts: list[str], labels=CUSTOM_LABELS, model_name: str = DEFAULT_SPACY_MODEL) -> list[list[dict]]:
    """Character-level entities per text, for evaluation against annotated spans (spec §17.1)."""
    nlp = load_ner_nlp(model_name)
    results = []
    for doc in nlp.pipe(texts, batch_size=64):
        results.append([
            {"start": e.start_char, "end": e.end_char, "text": e.text, "label": e.label_,
             "canonical": e.ent_id_ or e.text}
            for e in doc.ents if e.label_ in labels
        ])
    return results

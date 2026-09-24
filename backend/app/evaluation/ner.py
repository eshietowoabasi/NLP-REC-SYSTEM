"""NER evaluation (spec §17.1): 50 job adverts, two annotators, Precision/Recall/F1.

Input: JSON Lines, one advert per line:

    {"id": "ad-001", "text": "...",
     "annotator_a": [{"start": 10, "end": 20, "label": "TOOL"}, ...],
     "annotator_b": [...],
     "gold": [...]}                      # adjudicated labels (optional)

Entities can be character spans ({start, end, label}) or, if offsets are impractical to
record, names ({text, label}); names are compared per advert (document level).
Without "gold", annotator A's labels are used and a warning is reported.
"""
from ..services.ner import CUSTOM_LABELS, entity_spans
from .metrics import cohen_kappa, match_mentions, match_spans, prf

TARGETS = {"precision": 0.80, "recall": 0.75, "f1": 0.75}  # spec §17.1


def _is_span(entity):
    return "start" in entity and "end" in entity


def _mention_set(entities, text=None):
    names = set()
    for e in entities:
        name = e.get("canonical") or e.get("text") or (text[e["start"]:e["end"]] if text else "")
        names.add((" ".join(name.lower().split()), e["label"]))
    return names


def _validate(records):
    errors = []
    for i, r in enumerate(records, start=1):
        if not isinstance(r.get("text"), str) or not r["text"].strip():
            errors.append(f"line {i}: missing text")
        for key in ("annotator_a", "annotator_b", "gold"):
            for e in r.get(key) or []:
                if "label" not in e or not (_is_span(e) or "text" in e):
                    errors.append(f"line {i}: {key} entity needs a label and either start/end or text")
                elif _is_span(e) and not (0 <= e["start"] < e["end"] <= len(r["text"])):
                    errors.append(f"line {i}: {key} span {e['start']}-{e['end']} is outside the text")
    if errors:
        raise ValueError("Invalid annotation file:\n" + "\n".join(errors[:20]))


def _compare(gold, predicted, text, mode):
    if gold and all(_is_span(e) for e in gold) and mode != "document":
        return match_spans(gold, predicted, mode)
    # Document level: surface text or canonical name may match the annotator's name.
    gold_set = _mention_set(gold, text)
    pred_names = {(" ".join(p["text"].lower().split()), p["label"]) for p in predicted} | _mention_set(predicted)
    tp = len(gold_set & pred_names)
    return tp, max(len(_mention_set(predicted)) - tp, 0), len(gold_set) - tp


def _token_labels(text, entities):
    """BIO-free token labels ("O" or entity label) for Cohen's kappa between annotators."""
    labels, pos = [], 0
    for token in text.split():
        start = text.index(token, pos)
        end = pos = start + len(token)
        label = next((e["label"] for e in entities if _is_span(e) and e["start"] < end and start < e["end"]), "O")
        labels.append(label)
    return labels


def evaluate_ner(records: list[dict], labels=CUSTOM_LABELS, mode: str = "strict") -> dict:
    _validate(records)
    warnings = []
    if any("gold" not in r for r in records):
        warnings.append("Some records have no adjudicated 'gold' labels; annotator A was used for those.")

    predictions = entity_spans([r["text"] for r in records], labels)
    totals = {"overall": [0, 0, 0], **{label: [0, 0, 0] for label in labels}}
    for record, predicted in zip(records, predictions):
        gold = [e for e in record.get("gold", record.get("annotator_a", [])) if e["label"] in labels]
        for label in ("overall", *labels):
            g = gold if label == "overall" else [e for e in gold if e["label"] == label]
            p = predicted if label == "overall" else [e for e in predicted if e["label"] == label]
            tp, fp, fn = _compare(g, p, record["text"], mode)
            totals[label][0] += tp
            totals[label][1] += fp
            totals[label][2] += fn

    scores = {label: prf(*counts) for label, counts in totals.items()}
    overall = scores["overall"]
    result = {
        "documents": len(records),
        "mode": mode,
        "labels": list(labels),
        "scores": scores,
        "targets": TARGETS,
        "meets_targets": {k: overall[k] > v for k, v in TARGETS.items()},  # spec: "above"
        "warnings": warnings,
    }

    # Inter-annotator agreement (spec: two annotators).
    pairs = [r for r in records if r.get("annotator_a") is not None and r.get("annotator_b") is not None]
    if pairs:
        agree = [0, 0, 0]
        tokens_a, tokens_b = [], []
        for r in pairs:
            a = [e for e in r["annotator_a"] if e["label"] in labels]
            b = [e for e in r["annotator_b"] if e["label"] in labels]
            tp, fp, fn = _compare(a, b, r["text"], mode)
            agree = [agree[0] + tp, agree[1] + fp, agree[2] + fn]
            if all(_is_span(e) for e in a + b):
                tokens_a += _token_labels(r["text"], a)
                tokens_b += _token_labels(r["text"], b)
        result["inter_annotator"] = {
            "documents": len(pairs),
            "pairwise_f1": prf(*agree)["f1"],
            "cohen_kappa_tokens": cohen_kappa(tokens_a, tokens_b) if tokens_a else None,
        }
    if len(records) < 50:
        warnings.append(f"The evaluation plan calls for 50 job adverts; this file has {len(records)}.")
    return result

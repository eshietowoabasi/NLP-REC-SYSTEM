"""`flask eval …` commands for the evaluation plan (spec §17).

Each command prints a summary and writes full results as JSON (default
reports/evaluation/<name>-<timestamp>.json) for the project write-up.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import current_app
from flask.cli import AppGroup

eval_cli = AppGroup("eval", help="Evaluation plan (spec §17): NER, topics, similarity, SUS, performance.")


def _save(name, result, output):
    path = Path(output) if output else (
        Path(current_app.config["REPORT_FOLDER"]) / "evaluation"
        / f"{name}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    click.echo(f"\nFull results: {path}")


def _warnings(result):
    for warning in result.get("warnings", []):
        click.secho(f"Warning: {warning}", fg="yellow")


def _read_documents(input_dir):
    from ..models import FileType
    from ..services.ingestion import parse_document

    texts = []
    for path in sorted(Path(input_dir).iterdir()):
        suffix = path.suffix.lower().lstrip(".")
        if suffix in ("pdf", "docx", "txt"):
            texts.append(parse_document(path.read_bytes(), FileType(suffix)).text)
    if not texts:
        raise click.ClickException(f"No PDF, DOCX or TXT files in {input_dir}")
    return texts


def _embedder(backend):
    from ..services.embeddings import get_embedder

    return get_embedder(backend or current_app.config["EMBEDDING_BACKEND"], current_app.config["SBERT_MODEL"])


@eval_cli.command("ner")
@click.argument("annotations", type=click.Path(exists=True, dir_okay=False))
@click.option("--mode", type=click.Choice(["strict", "lenient", "document"]), default="strict", show_default=True,
              help="strict: exact spans; lenient: overlapping spans; document: entity names per advert.")
@click.option("--output", type=click.Path(dir_okay=False), help="Where to write the JSON results.")
def eval_ner(annotations, mode, output):
    """NER precision / recall / F1 against annotated job adverts (JSONL)."""
    from .ner import evaluate_ner

    records = [json.loads(line) for line in Path(annotations).read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        result = evaluate_ner(records, mode=mode)
    except ValueError as exc:
        raise click.ClickException(str(exc))
    click.echo(f"NER evaluation ({result['documents']} adverts, {mode} matching)")
    click.echo(f"{'label':<10}{'precision':>10}{'recall':>10}{'f1':>10}{'tp':>6}{'fp':>6}{'fn':>6}")
    for label, s in result["scores"].items():
        click.echo(f"{label:<10}{s['precision']:>10.3f}{s['recall']:>10.3f}{s['f1']:>10.3f}{s['tp']:>6}{s['fp']:>6}{s['fn']:>6}")
    click.echo("Targets (P>0.80, R>0.75, F1>0.75): " + ", ".join(
        f"{k} {'met' if v else 'NOT met'}" for k, v in result["meets_targets"].items()))
    if "inter_annotator" in result:
        ia = result["inter_annotator"]
        click.echo(f"Inter-annotator agreement: pairwise F1 {ia['pairwise_f1']}, token kappa {ia['cohen_kappa_tokens']}")
    _warnings(result)
    _save("ner", result, output)


@eval_cli.command("topics")
@click.option("--input-dir", type=click.Path(exists=True, file_okay=False), help="Folder of PDF/DOCX/TXT documents.")
@click.option("--session-id", type=int, help="Use the documents of an existing analysis session.")
@click.option("--backend", type=click.Choice(["sbert", "hashing"]), help="Embedding backend (default: configured).")
@click.option("--output", type=click.Path(dir_okay=False))
def eval_topics(input_dir, session_id, backend, output):
    """Topic coherence (C_v) and diversity: BERTopic vs LDA."""
    from .topics import evaluate_topics

    if bool(input_dir) == bool(session_id):
        raise click.UsageError("Give exactly one of --input-dir or --session-id")
    if input_dir:
        texts = _read_documents(input_dir)
    else:
        from sqlalchemy import select
        from sqlalchemy.orm import undefer

        from ..extensions import db
        from ..models import Document, DocumentSession, SourceCategory

        texts = [d.extracted_text for d in db.session.execute(
            select(Document).join(DocumentSession).where(DocumentSession.session_id == session_id,
                                                         Document.source_category != SourceCategory.NUC_CORE)
            .options(undefer(Document.extracted_text))).scalars() if d.extracted_text]
    try:
        result = evaluate_topics(texts, _embedder(backend))
    except ValueError as exc:
        raise click.ClickException(str(exc))
    click.echo(f"Topic evaluation: {result['documents']} documents, {result['passages']} passages, {result['num_topics']} topics")
    for name in ("bertopic", "lda"):
        r = result[name]
        click.echo(f"  {name:<9} C_v {r['c_v']:.4f}   diversity {r['diversity']:.3f}   {r['seconds']} s")
    click.echo(f"Higher coherence: {result['better_coherence']}")
    _warnings(result)
    _save("topics", result, output)


@eval_cli.command("similarity")
@click.argument("pairs_csv", type=click.Path(exists=True, dir_okay=False))
@click.option("--threshold", type=float, default=0.80, show_default=True)
@click.option("--backend", type=click.Choice(["sbert", "hashing"]), help="Embedding backend (default: configured).")
@click.option("--output", type=click.Path(dir_okay=False))
def eval_similarity(pairs_csv, threshold, backend, output):
    """AUC-ROC of overlap detection on expert-labelled topic pairs (CSV)."""
    from .similarity import evaluate_similarity, load_pairs_csv

    try:
        result = evaluate_similarity(load_pairs_csv(pairs_csv), _embedder(backend), threshold)
    except ValueError as exc:
        raise click.ClickException(str(exc))
    at, best = result["at_configured_threshold"], result["youden_optimal"]
    click.echo(f"Semantic overlap evaluation: {result['pairs']} pairs, model {result['embedding_model']}")
    click.echo(f"  AUC-ROC {result['auc_roc']:.4f}")
    click.echo(f"  at threshold {threshold}: precision {at['precision']:.3f}, recall {at['recall']:.3f}, F1 {at['f1']:.3f}")
    click.echo(f"  Youden-optimal threshold {best['threshold']}: precision {best['precision']:.3f}, "
               f"recall {best['recall']:.3f}, F1 {best['f1']:.3f}")
    _warnings(result)
    _save("similarity", result, output)


@eval_cli.command("sus")
@click.argument("responses_csv", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", type=click.Path(dir_okay=False))
def eval_sus(responses_csv, output):
    """System Usability Scale scores from UAT questionnaires (CSV: respondent_id, q1..q10)."""
    from .sus import evaluate_sus, load_sus_csv

    try:
        result = evaluate_sus(load_sus_csv(responses_csv))
    except ValueError as exc:
        raise click.ClickException(str(exc))
    click.echo(f"SUS: n={result['n']}, mean {result['mean']} (SD {result['sd']}, range {result['min']}-{result['max']}), "
               f"grade {result['grade']}; target >= {result['target_mean']}: {'met' if result['meets_target'] else 'NOT met'}")
    _warnings(result)
    _save("sus", result, output)


@eval_cli.command("performance")
@click.option("--documents", default=20, show_default=True)
@click.option("--words", default=3000, show_default=True, help="Approximate words per synthetic document.")
@click.option("--input-dir", type=click.Path(exists=True, file_okay=False), help="Use real documents instead.")
@click.option("--backend", type=click.Choice(["sbert", "hashing"]), help="Embedding backend (default: configured).")
@click.option("--output", type=click.Path(dir_okay=False))
def eval_performance(documents, words, input_dir, backend, output):
    """Time the full pipeline (spec §17.5 target: <= 60 s for 20 x 3,000 words)."""
    from .performance import benchmark, synthetic_corpus

    texts = _read_documents(input_dir) if input_dir else synthetic_corpus(documents, words)
    core = synthetic_corpus(1, 800, seed=99)[0]
    result = benchmark(texts, core, backend or current_app.config["EMBEDDING_BACKEND"], current_app.config["SBERT_MODEL"])
    click.echo(f"Pipeline: {result['documents']} documents, {result['words']} words -> {result['wall_seconds']} s "
               f"(target {result['target_seconds']} s: {'met' if result['meets_target'] else 'NOT met'})")
    click.echo("  " + ", ".join(f"{k} {v}s" for k, v in result["stage_seconds"].items()))
    _warnings(result)
    _save("performance", result, output)

"""Score ontology-term answers against their curated value, with no judge.

For tasks whose answer is one ``label [CURIE]`` term and whose cases carry an ``ideal``, such as
nmdc-ebs. Following docs/criteria.md, each check is reported on its own rather than folded into one
number:

* tier 1, against a formal spec: the answer parses, its CURIE exists in ENVO, its label is ENVO's
  label for that CURIE.
* tier 2, against ontology structure: exact match, and otherwise whether the answer is an ancestor
  (vaguer), a descendant (more specific) or unrelated to the curated term, with the hop count.

The ENVO checks reuse ``nmdc_ai_eval.envo_scorer`` unchanged. Its composite ``hierarchy_score`` is
also recorded, for continuity with nmdc-ai-eval results, though docs/criteria.md questions its
weights. The per-template enum check is left out: its data lives outside nmdc-ai-eval's package.

Usage: ``uv run python -m local_llm_evals.ontology_scoring results/runs/nmdc-ebs/<batch>``
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from local_llm_evals.runner import REPO_ROOT

SCORES_DIR = REPO_ROOT / "results" / "scores"
COLUMNS = [
    "case_id",
    "model_id",
    "run_index",
    "ideal",
    "response",
    "parsed",
    "curie_resolves",
    "label_matches",
    "exact",
    "ideal_label_matches",
    "relationship",
    "hops",
    "hierarchy_score",
    "error",
]


def score_answer(response: str, ideal: str, adapter: Any) -> dict[str, Any]:
    """Every check for one answer. ``adapter`` is an oaklib ENVO adapter or a stand-in with
    ``label``; relationship and hops come from envo_scorer, which also needs ``ancestors``."""
    from nmdc_ai_eval.envo_scorer import (
        check_relationship,
        compute_hierarchy_score,
        compute_hop_distance,
        parse_label_curie,
    )

    row: dict[str, Any] = {"parsed": False}
    answer = parse_label_curie(response or "")
    truth = parse_label_curie(ideal)
    if answer is None or truth is None:
        return row
    label, curie = answer
    canonical = adapter.label(curie)
    ideal_canonical = adapter.label(truth[1])
    # The curated value gets the same tier 1 check as the answer. When its label is not ENVO's
    # label for its CURIE, the reference itself is suspect, and a disagreement with it is not
    # evidence the answer is wrong.
    row["ideal_label_matches"] = bool(ideal_canonical and ideal_canonical.lower() == truth[0].lower())
    relationship = check_relationship(adapter, curie, truth[1])
    hops = None if relationship in ("exact", "unrelated") else compute_hop_distance(adapter, curie, truth[1])
    row.update(
        parsed=True,
        curie_resolves=canonical is not None,
        label_matches=bool(canonical and canonical.lower() == label.lower()),
        exact=curie == truth[1],
        relationship=relationship,
        hops=hops,
        hierarchy_score=round(compute_hierarchy_score(relationship, hops), 3),
    )
    return row


def score_batch(batch_dir: Path, adapter: Any = None) -> Path:
    """Score every run file in a batch and write ``ontology.tsv`` beside the other score files."""
    if adapter is None:
        from nmdc_ai_eval.envo_scorer import get_envo_adapter

        adapter = get_envo_adapter()
    rows = []
    for path in sorted(batch_dir.glob("*.yaml")):
        record = yaml.safe_load(path.read_text())
        if not record.get("ideal"):
            continue
        row = {k: record.get(k) for k in ("case_id", "model_id", "run_index", "ideal", "response", "error")}
        if not record.get("error"):
            row.update(score_answer(record.get("response", ""), record["ideal"], adapter))
        rows.append(row)
    out_dir = SCORES_DIR / batch_dir.parent.name / batch_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "ontology.tsv"
    with open(out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _cell(row.get(k)) for k in COLUMNS})
    return out


def summarize(tsv: Path) -> list[dict[str, Any]]:
    """Per model: counts of each check, with the number of answers as the denominator."""
    per_model: dict[str, list[dict[str, str]]] = defaultdict(list)
    with open(tsv) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            per_model[row["model_id"]].append(row)
    summary = []
    for model, rows in sorted(per_model.items()):
        counts = {
            "model_id": model,
            "answers": len(rows),
            "errors": sum(1 for r in rows if r["error"]),
            "parsed": sum(1 for r in rows if r["parsed"] == "true"),
            "curie_resolves": sum(1 for r in rows if r["curie_resolves"] == "true"),
            "label_matches": sum(1 for r in rows if r["label_matches"] == "true"),
            "exact": sum(1 for r in rows if r["exact"] == "true"),
            "suspect_reference": sum(1 for r in rows if r["ideal_label_matches"] == "false"),
            "exact_on_sound_reference": sum(
                1 for r in rows if r["exact"] == "true" and r["ideal_label_matches"] == "true"
            ),
            "matches_suspect_reference_label": sum(
                1
                for r in rows
                if r["ideal_label_matches"] == "false"
                and r["label_matches"] == "true"
                and r["response"].rsplit(" [", 1)[0].lower() == r["ideal"].rsplit(" [", 1)[0].lower()
            ),
        }
        for kind in ("descendant", "ancestor", "unrelated"):
            counts[kind] = sum(1 for r in rows if r["relationship"] == kind)
        summary.append(counts)
    return summary


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\t", " ").replace("\n", " ")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m local_llm_evals.ontology_scoring results/runs/<task>/<batch>")
    out = score_batch(Path(sys.argv[1]))
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    for row in summarize(out):
        print("\t".join(f"{k}={v}" for k, v in row.items()))


if __name__ == "__main__":
    main()

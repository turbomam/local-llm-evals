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


def ideal_is_sound(ideal: str, adapter: Any) -> bool:
    """The curated value gets the same tier 1 check as an answer, independent of any answer.

    When its label is not ENVO's label for its CURIE, or it does not parse, the reference itself is
    suspect, and a disagreement with it is not evidence the answer is wrong.
    """
    from nmdc_ai_eval.envo_scorer import parse_label_curie

    truth = parse_label_curie(ideal or "")
    if truth is None:
        return False
    canonical = adapter.label(truth[1])
    return bool(canonical and canonical.lower() == truth[0].lower())


def score_answer(response: str, ideal: str, adapter: Any) -> dict[str, Any]:
    """Every check for one answer. ``adapter`` is an oaklib ENVO adapter or a stand-in with
    ``label``; relationship and hops come from envo_scorer, which also needs ``ancestors``."""
    from nmdc_ai_eval.envo_scorer import (
        check_relationship,
        compute_hierarchy_score,
        compute_hop_distance,
        parse_label_curie,
    )

    row: dict[str, Any] = {"parsed": False, "ideal_label_matches": ideal_is_sound(ideal, adapter)}
    answer = parse_label_curie(response or "")
    if answer is None:
        return row
    # Tier 1 depends only on the answer, so it runs even when the curated value is malformed.
    label, curie = answer
    canonical = adapter.label(curie)
    row.update(
        parsed=True,
        curie_resolves=canonical is not None,
        label_matches=bool(canonical and canonical.lower() == label.lower()),
    )
    truth = parse_label_curie(ideal or "")
    if truth is None:
        return row
    relationship = check_relationship(adapter, curie, truth[1])
    hops = None if relationship in ("exact", "unrelated") else compute_hop_distance(adapter, curie, truth[1])
    row.update(
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
        # Checked for every record, failed runs included, so the count does not depend on answers.
        row["ideal_label_matches"] = ideal_is_sound(record["ideal"], adapter)
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


def summarize_spread(tsv: Path) -> list[dict[str, Any]]:
    """Per model, each count's lowest and highest value across runs of the same cases.

    Only cases whose curated value is sound count, so a wrong reference cannot inflate
    "unrelated". Only cases present in every run count, so an interrupted batch cannot turn
    missing rows into apparent variation. These are observed ranges, not confidence intervals.
    """
    per_model_run: dict[str, dict[str, dict[str, dict[str, str]]]] = defaultdict(lambda: defaultdict(dict))
    with open(tsv) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row.get("ideal_label_matches") != "true":
                continue
            per_model_run[row["model_id"]][row["run_index"]][row["case_id"]] = row
    keys = ("label_matches", "exact", "descendant", "ancestor", "unrelated")
    spread = []
    for model, runs in sorted(per_model_run.items()):
        common = set.intersection(*(set(cases) for cases in runs.values()))
        dropped = sum(len(cases) for cases in runs.values()) - len(common) * len(runs)
        per_run = []
        for cases in runs.values():
            rows = [cases[c] for c in common]
            counts = {k: sum(1 for r in rows if r.get(k) == "true") for k in ("label_matches", "exact")}
            counts.update({k: sum(1 for r in rows if r["relationship"] == k) for k in keys[2:]})
            per_run.append(counts)
        entry: dict[str, Any] = {
            "model_id": model,
            "runs": len(runs),
            "cases_in_every_run": len(common),
            "rows_left_out": dropped,
        }
        for k in keys:
            values = [c[k] for c in per_run]
            entry[k] = f"{min(values)}-{max(values)}" if min(values) != max(values) else str(values[0])
        spread.append(entry)
    return spread


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
    print("spread across runs, sound references and cases in every run only (lowest-highest):")
    for row in summarize_spread(out):
        print("\t".join(f"{k}={v}" for k, v in row.items()))


if __name__ == "__main__":
    main()

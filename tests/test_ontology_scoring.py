"""Ontology scoring against a hand-written ENVO fragment. No network, no ontology download."""

from __future__ import annotations

from local_llm_evals.ontology_scoring import score_answer

# forest biome <- temperate broadleaf forest biome; biome at the top. One unrelated term.
LABELS = {
    "ENVO:00000428": "biome",
    "ENVO:01000174": "forest biome",
    "ENVO:01000202": "temperate broadleaf forest biome",
    "ENVO:01000245": "cropland biome",
}
PARENTS = {
    "ENVO:01000174": ["ENVO:00000428"],
    "ENVO:01000202": ["ENVO:01000174"],
    "ENVO:01000245": ["ENVO:00000428"],
}


class FakeEnvo:
    def label(self, curie):
        return LABELS.get(curie)

    def ancestors(self, curie, predicates=None):
        seen, stack = [], [curie]
        while stack:
            node = stack.pop()
            seen.append(node)
            stack.extend(PARENTS.get(node, []))
        return seen

    def hierarchical_parents(self, curie):
        return PARENTS.get(curie, [])


ENVO = FakeEnvo()
IDEAL = "forest biome [ENVO:01000174]"


def test_exact_answer() -> None:
    row = score_answer("forest biome [ENVO:01000174]", IDEAL, ENVO)
    assert row["parsed"] and row["curie_resolves"] and row["label_matches"] and row["exact"]
    assert row["relationship"] == "exact"


def test_more_specific_answer_is_a_descendant() -> None:
    row = score_answer("temperate broadleaf forest biome [ENVO:01000202]", IDEAL, ENVO)
    assert not row["exact"]
    assert row["relationship"] == "descendant"
    assert row["hops"] == 1


def test_vaguer_answer_is_an_ancestor() -> None:
    row = score_answer("biome [ENVO:00000428]", IDEAL, ENVO)
    assert row["relationship"] == "ancestor"
    assert row["hops"] == 1


def test_label_on_the_wrong_curie_is_caught() -> None:
    row = score_answer("forest biome [ENVO:01000245]", IDEAL, ENVO)
    assert row["curie_resolves"] and not row["label_matches"]
    assert row["relationship"] == "unrelated"


def test_prose_answer_does_not_parse() -> None:
    assert score_answer("I think it is a forest.", IDEAL, ENVO) == {"parsed": False, "ideal_label_matches": True}


def test_a_curated_value_with_the_wrong_curie_is_flagged() -> None:
    """The reference gets the same check as the answer, so a bad reference is visible."""
    bad_ideal = "forest biome [ENVO:01000245]"  # ENVO:01000245 is cropland biome
    row = score_answer("forest biome [ENVO:01000174]", bad_ideal, ENVO)
    assert row["ideal_label_matches"] is False
    assert row["label_matches"] is True
    assert row["relationship"] == "unrelated"


def test_a_sound_curated_value_is_not_flagged() -> None:
    assert score_answer("forest biome [ENVO:01000174]", IDEAL, ENVO)["ideal_label_matches"] is True


def test_a_bad_reference_is_flagged_even_when_the_answer_does_not_parse() -> None:
    """The reference check must not depend on the answer, or its count varies by model."""
    row = score_answer("no idea", "forest biome [ENVO:01000245]", ENVO)
    assert row["parsed"] is False
    assert row["ideal_label_matches"] is False


def test_score_batch_checks_the_reference_on_failed_runs(tmp_path, monkeypatch) -> None:
    import csv

    import yaml

    from local_llm_evals import ontology_scoring

    batch = tmp_path / "nmdc-ebs" / "b1"
    batch.mkdir(parents=True)
    (batch / "case000-m-run1.yaml").write_text(
        yaml.safe_dump({"case_id": "case000", "model_id": "m", "run_index": 1,
                        "ideal": "forest biome [ENVO:01000245]", "response": "", "error": "boom"})
    )
    monkeypatch.setattr(ontology_scoring, "SCORES_DIR", tmp_path / "scores")
    out = ontology_scoring.score_batch(batch, adapter=ENVO)
    rows = list(csv.DictReader(open(out), delimiter="\t"))
    assert rows[0]["ideal_label_matches"] == "false"


def test_answer_checks_survive_a_malformed_reference() -> None:
    """A curated value that does not parse must not make a good answer look unparsable."""
    row = score_answer("forest biome [ENVO:01000174]", "not a term", ENVO)
    assert row["parsed"] is True
    assert row["curie_resolves"] is True and row["label_matches"] is True
    assert row["ideal_label_matches"] is False
    assert "relationship" not in row and "exact" not in row


def _write_tsv(path, rows):
    from local_llm_evals.ontology_scoring import COLUMNS

    with open(path, "w") as handle:
        handle.write("\t".join(COLUMNS) + "\n")
        for row in rows:
            full = {"ideal_label_matches": "true", **row}
            handle.write("\t".join(full.get(c, "") for c in COLUMNS) + "\n")


def _r(run, case, exact, label="true", rel=None, sound="true"):
    return {"model_id": "m", "run_index": run, "case_id": case, "exact": exact, "label_matches": label,
            "relationship": rel or ("exact" if exact == "true" else "unrelated"), "ideal_label_matches": sound}


def test_spread_reports_the_range_across_runs(tmp_path) -> None:
    from local_llm_evals.ontology_scoring import summarize_spread

    tsv = tmp_path / "ontology.tsv"
    _write_tsv(tsv, [_r("1", "a", "true"), _r("1", "b", "false"), _r("2", "a", "false"), _r("2", "b", "false", "false")])
    (entry,) = summarize_spread(tsv)
    assert entry["runs"] == 2 and entry["cases_in_every_run"] == 2
    assert entry["exact"] == "0-1"
    assert entry["label_matches"] == "1-2"


def test_spread_leaves_out_suspect_references(tmp_path) -> None:
    """A correct answer to a wrong reference must not count as unrelated."""
    from local_llm_evals.ontology_scoring import summarize_spread

    tsv = tmp_path / "ontology.tsv"
    _write_tsv(tsv, [_r("1", "a", "true"), _r("1", "bad", "false", sound="false"),
                     _r("2", "a", "true"), _r("2", "bad", "false", sound="false")])
    (entry,) = summarize_spread(tsv)
    assert entry["cases_in_every_run"] == 1
    assert entry["unrelated"] == "0"


def test_spread_uses_only_cases_present_in_every_run(tmp_path) -> None:
    """An interrupted run must not show up as model variation."""
    from local_llm_evals.ontology_scoring import summarize_spread

    tsv = tmp_path / "ontology.tsv"
    _write_tsv(tsv, [_r("1", "a", "true"), _r("1", "b", "true"), _r("2", "a", "true")])
    (entry,) = summarize_spread(tsv)
    assert entry["cases_in_every_run"] == 1
    assert entry["rows_left_out"] == 1
    assert entry["exact"] == "1"


def test_spread_leaves_out_failed_calls(tmp_path) -> None:
    """A timeout in one run must not show up as a lower score for that run."""
    from local_llm_evals.ontology_scoring import summarize_spread

    tsv = tmp_path / "ontology.tsv"
    failed = {**_r("2", "b", "false"), "error": "timeout", "exact": "", "label_matches": "", "relationship": ""}
    _write_tsv(tsv, [_r("1", "a", "true"), _r("1", "b", "true"), _r("2", "a", "true"), failed])
    (entry,) = summarize_spread(tsv)
    assert entry["exact"] == "1"
    assert entry["cases_in_every_run"] == 1
    assert entry["failed_calls"] == 1


def _failed(run, case):
    return {**_r(run, case, "false"), "error": "timeout", "exact": "", "label_matches": "", "relationship": ""}


def test_a_run_where_every_call_failed_still_counts(tmp_path) -> None:
    from local_llm_evals.ontology_scoring import summarize_spread

    tsv = tmp_path / "ontology.tsv"
    _write_tsv(tsv, [_r("1", "a", "true"), _failed("2", "a")])
    (entry,) = summarize_spread(tsv)
    assert entry["runs"] == 2
    assert entry["cases_in_every_run"] == 0
    assert entry["failed_calls"] == 1


def test_a_model_whose_every_call_failed_is_still_reported(tmp_path) -> None:
    from local_llm_evals.ontology_scoring import summarize_spread

    tsv = tmp_path / "ontology.tsv"
    _write_tsv(tsv, [_failed("1", "a"), _failed("2", "a")])
    (entry,) = summarize_spread(tsv)
    assert entry["runs"] == 2
    assert entry["failed_calls"] == 2

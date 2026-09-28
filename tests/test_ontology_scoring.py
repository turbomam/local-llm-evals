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
    assert score_answer("I think it is a forest.", IDEAL, ENVO) == {"parsed": False}


def test_a_curated_value_with_the_wrong_curie_is_flagged() -> None:
    """The reference gets the same check as the answer, so a bad reference is visible."""
    bad_ideal = "forest biome [ENVO:01000245]"  # ENVO:01000245 is cropland biome
    row = score_answer("forest biome [ENVO:01000174]", bad_ideal, ENVO)
    assert row["ideal_label_matches"] is False
    assert row["label_matches"] is True
    assert row["relationship"] == "unrelated"


def test_a_sound_curated_value_is_not_flagged() -> None:
    assert score_answer("forest biome [ENVO:01000174]", IDEAL, ENVO)["ideal_label_matches"] is True

# List recipes
default:
    @just --list

# Show which models would run and why others are skipped
dry-run task="photosynthesis":
    uv run local-llm-evals run --task {{task}} --dry-run

# Run a task; pass model ids to limit it, e.g. just run photosynthesis 3 m5-fm-system
run task="photosynthesis" runs="3" models="":
    uv run local-llm-evals run --task {{task}} --runs {{runs}} {{ if models != "" { "--models " + models } else { "" } }}

# Score every run in a batch directory, e.g. just score results/runs/photosynthesis/<batch-id>
score batch:
    uv run local-llm-evals score {{batch}}

# Run the unit tests
test:
    uv run pytest -q tests

# Validate every run file and score file against its LinkML schema
check:
    #!/usr/bin/env bash
    set -euo pipefail
    # One linkml call per schema: starting Python once per file took 10 minutes in CI.
    validate() {
        local dir=$1 schema=$2 class=$3 label=$4 files=()
        while IFS= read -r f; do files+=("$f"); done < <(find "$dir" -name '*.yaml' 2>/dev/null | sort)
        if [ ${#files[@]} -eq 0 ]; then echo "0 $label files"; return; fi
        local out
        out=$(uv run linkml validate --schema "$schema" --target-class "$class" "${files[@]}" 2>&1) \
            || { echo "$out"; exit 1; }
        echo "${#files[@]} $label files valid"
    }
    validate results/runs schema/run_result.yaml RunResult run
    validate results/scores schema/score_result.yaml ScoreResult score

# Score ontology-term answers against their curated values (no judge), e.g. for nmdc-ebs
score-ontology batch:
    uv run python -m local_llm_evals.ontology_scoring {{batch}}

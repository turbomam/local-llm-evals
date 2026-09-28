# List recipes
default:
    @just --list

# Show which models would run and why others are skipped
dry-run task="photosynthesis":
    uv run local-llm-evals run --task {{task}} --dry-run

# Run a task; pass model ids to limit it, e.g. just run photosynthesis 3 m5-fm-system
run task="photosynthesis" runs="3" models="":
    uv run local-llm-evals run --task {{task}} --runs {{runs}} {{ if models != "" { "--models " + models } else { "" } }}

# Run the unit tests
test:
    uv run pytest -q tests

# Validate every result file against the LinkML schema
check:
    #!/usr/bin/env bash
    set -euo pipefail
    count=0
    while IFS= read -r f; do
        uv run linkml validate --schema schema/run_result.yaml --target-class RunResult "$f" >/dev/null \
            || { echo "invalid: $f"; exit 1; }
        count=$((count + 1))
    done < <(find results/runs -name '*.yaml' 2>/dev/null | sort)
    echo "$count result files valid"

# Score ontology-term answers against their curated values (no judge), e.g. for nmdc-ebs
score-ontology batch:
    uv run python -m local_llm_evals.ontology_scoring {{batch}}

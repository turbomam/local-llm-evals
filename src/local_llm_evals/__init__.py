"""Command line: `uv run local-llm-evals run --task photosynthesis --runs 3`."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return number


def score_batch(batch_dir: Path, force: bool) -> None:
    from local_llm_evals import runner, scoring

    batch_dir = batch_dir.resolve()
    run_files = sorted(batch_dir.glob("*.yaml"))
    if not run_files:
        sys.exit(f"no run files in {batch_dir}")
    models = {m["id"]: m for m in runner.load_models()}
    judges = yaml.safe_load(scoring.JUDGES_FILE.read_text())["judges"]
    langfuse = runner.langfuse_client()
    print("langfuse: " + ("recording scores" if langfuse else "off (no keys in .env)"))
    tasks: dict[str, dict] = {}
    for run_file in run_files:
        run = yaml.safe_load(run_file.read_text())
        task = tasks.setdefault(run["task_id"], runner.load_task(run["task_id"]))
        # Skip only when the judge this run would get now has already scored it, so a newly
        # available preferred judge (e.g. Gemini replacing a provisional one) rescores the run.
        judge_id = scoring.expected_judge_id(run, judges, models)
        existing = scoring.SCORES_DIR / run["task_id"] / run["batch_id"] / f"{run_file.stem}.{judge_id}.yaml"
        if existing.exists() and not force:
            if not scoring.needs_retry(yaml.safe_load(existing.read_text())):
                print(f"{run_file.stem}: already scored by {judge_id}; use --force to rescore")
                continue
            print(f"{run_file.stem}: retrying, the cached score recorded an error", flush=True)
        scores = scoring.score_run(run_file, task, judges, models)
        scoring.send_to_langfuse(langfuse, run.get("langfuse_trace_id"), scores)
        path = scoring.write_scores(scores)
        summary = scores.get("scoring_error") or (
            f"checklist {scores['checklist_present']}/{scores['checklist_total']}, "
            f"false {scores['false_statement_count']}, relevancy {scores['relevancy']}, "
            f"coherence {scores['coherence']}, judge {scores['judge_model_id']} ({scores['judge_status']})"
        )
        print(f"{run_file.stem}: {summary} -> {path.relative_to(runner.REPO_ROOT)}", flush=True)
    if langfuse:
        try:
            langfuse.flush()
        except Exception as exc:  # score files are already written; say so rather than crash
            print(
                f"langfuse: flush failed ({type(exc).__name__}: {exc}); score files are written, "
                "but some scores may not have reached Langfuse",
                file=sys.stderr,
            )
            sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(prog="local-llm-evals")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run one task on the configured models")
    run.add_argument("--task", required=True, help="task id, a file name in tasks/ without .yaml")
    run.add_argument("--models", help="comma-separated model ids; default is every runnable model")
    run.add_argument("--runs", type=positive_int, default=3, help="runs per model (default 3)")
    run.add_argument(
        "--dry-run", action="store_true", help="list which models would run and why others are skipped"
    )
    score = commands.add_parser("score", help="score every run file in one batch directory")
    score.add_argument("batch", help="batch directory, e.g. results/runs/photosynthesis/<batch-id>")
    score.add_argument("--force", action="store_true", help="rescore runs that already have a score file")
    args = parser.parse_args()

    # Load .env before anything imports langfuse, which reads its settings at import time.
    from local_llm_evals import runner

    load_dotenv(runner.REPO_ROOT / ".env")

    if args.command == "score":
        score_batch(Path(args.batch), args.force)
        return

    task = runner.load_task(args.task)
    wanted = set(args.models.split(",")) if args.models else None
    specs = [m for m in runner.load_models() if wanted is None or m["id"] in wanted]
    if wanted and (unknown := wanted - {m["id"] for m in specs}):
        sys.exit(f"unknown model ids: {', '.join(sorted(unknown))}")

    endpoints = []
    for spec in specs:
        resolved = runner.resolve(spec)
        if isinstance(resolved, str):
            print(f"skip {spec['id']}: {resolved}")
        else:
            endpoints.append(resolved)
            print(f"run  {spec['id']}: {resolved.base_url} model={spec['model']}")

    langfuse = runner.langfuse_client()
    print("langfuse: " + ("recording" if langfuse else "off (no keys in .env)"))
    if args.dry_run or not endpoints:
        return

    # Microseconds, so two invocations started in the same second get separate directories.
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    commit = runner.repo_commit()
    for endpoint in endpoints:
        for run_index in range(1, args.runs + 1):
            record = runner.run_once(endpoint, task, run_index, batch_id, commit, langfuse)
            path = runner.write_record(record)
            summary = record.get("error") or (
                f"{record.get('output_tokens', '?')} tokens, "
                f"{record.get('decode_tokens_per_second', 0):.1f} tokens/s, "
                f"{record.get('total_seconds', 0):.1f} s"
            )
            print(
                f"{endpoint.spec['id']} run {run_index}: {summary} -> {path.relative_to(runner.REPO_ROOT)}",
                flush=True,
            )
    if langfuse:
        langfuse.flush()

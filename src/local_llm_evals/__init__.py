"""Command line: `uv run local-llm-evals run --task photosynthesis --runs 3`."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return number


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
    args = parser.parse_args()

    # Load .env before anything imports langfuse, which reads its settings at import time.
    from local_llm_evals import runner

    load_dotenv(runner.REPO_ROOT / ".env")

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

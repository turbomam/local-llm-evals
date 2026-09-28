"""Send one task's prompt to each configured model and write one result file per run.

Every server is called through OpenAI's Chat Completions API with streaming, so time to first
token is measured the same way everywhere. When Langfuse keys are present in .env, each run is
also recorded as a Langfuse generation; without them the run still happens and is written to disk.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_FILE = REPO_ROOT / "config" / "models.yaml"
TASKS_DIR = REPO_ROOT / "tasks"
RUNS_DIR = REPO_ROOT / "results" / "runs"

# Local servers need no key, but the OpenAI client refuses an empty one.
PLACEHOLDER_KEY = "not-needed"


@dataclass
class Endpoint:
    """A configured model that has everything it needs to run."""

    spec: dict[str, Any]
    base_url: str
    api_key: str
    token_count_command: list[str] | None


def load_models() -> list[dict[str, Any]]:
    return yaml.safe_load(MODELS_FILE.read_text())["models"]


def load_task(task_id: str) -> dict[str, Any]:
    return yaml.safe_load((TASKS_DIR / f"{task_id}.yaml").read_text())


def task_cases(task: dict[str, Any]) -> list[dict[str, Any]]:
    """The cases a task asks each model: one for a single-prompt task, several for a case set.

    A task with ``source`` names a pinned upstream suite; its cases are fetched, not copied here,
    and ``select`` chooses which ones. Each case is ``{id, prompt, system?, ideal?}``.
    """
    if "source" not in task:
        return [{"id": task["id"], "prompt": task["prompt"], "system": task.get("system")}]
    suite = yaml.safe_load(fetch_text(task["source"]["url"]))
    system = suite["templates"][task["source"]["template"]]["system"]
    per_ideal = task["select"]["per_ideal"]
    taken: dict[str, int] = {}
    cases = []
    for index, case in enumerate(suite["cases"]):
        if taken.get(case["ideal"], 0) >= per_ideal:
            continue
        taken[case["ideal"]] = taken.get(case["ideal"], 0) + 1
        cases.append({"id": f"case{index:03d}", "prompt": case["input"], "system": system, "ideal": case["ideal"]})
    return cases


def fetch_text(url: str) -> str:
    """Fetch a pinned public file. Cached per process so a batch fetches it once."""
    if url not in _FETCHED:
        import urllib.request

        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - pinned https URL from a task file
            _FETCHED[url] = response.read().decode()
    return _FETCHED[url]


_FETCHED: dict[str, str] = {}


def resolve(spec: dict[str, Any]) -> Endpoint | str:
    """Return a runnable Endpoint, or a string saying why the model is skipped."""
    if not spec.get("model"):
        return "no model name in config/models.yaml"
    base_url = os.environ.get(spec["base_url_env"], "").strip()
    if not base_url:
        return f"{spec['base_url_env']} not set in .env"
    api_key = PLACEHOLDER_KEY
    if key_env := spec.get("api_key_env"):
        api_key = os.environ.get(key_env, "").strip()
        if not api_key:
            return f"{key_env} not set in .env"
    # Optional fallback, used only when the server reports no token usage.
    command = os.environ.get(spec.get("token_count_env", ""), "").strip()
    token_count_command = shlex.split(command) if command else None
    return Endpoint(
        spec=spec,
        base_url=base_url.rstrip("/") + spec.get("path", ""),
        api_key=api_key,
        token_count_command=token_count_command,
    )


def repo_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() or None


def count_tokens(command: list[str], text: str) -> int | None:
    """Best effort: a missing or failing counter leaves the count unknown, not the run failed."""
    try:
        result = subprocess.run(command, input=text, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip().split()[-1])
    except (ValueError, IndexError):
        return None


def stream_completion(endpoint: Endpoint, task: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Call the model once, streaming, and return what came back with timings."""
    from openai import BadRequestError, OpenAI

    client = OpenAI(base_url=endpoint.base_url, api_key=endpoint.api_key, timeout=1800)
    request = {
        "model": endpoint.spec["model"],
        "messages": messages_for(case),
        "max_tokens": task.get("max_tokens"),
        "stream": True,
    }
    sent = time.perf_counter()
    try:
        stream = client.chat.completions.create(**request, stream_options={"include_usage": True})
    except BadRequestError:
        # Not every server accepts stream_options; retry without asking for usage.
        sent = time.perf_counter()
        stream = client.chat.completions.create(**request)

    first = last = None
    content: list[str] = []
    reasoning: list[str] = []
    finish_reason = None
    usage = None
    for chunk in stream:
        if chunk.usage:
            usage = chunk.usage
        for choice in chunk.choices:
            delta = choice.delta
            extra = delta.model_extra or {}
            thought = extra.get("reasoning") or extra.get("reasoning_content")
            if delta.content or thought:
                last = time.perf_counter()
                first = first or last
            if delta.content:
                content.append(delta.content)
            if thought:
                reasoning.append(thought)
            if choice.finish_reason:
                finish_reason = choice.finish_reason
    done = time.perf_counter()

    return {
        "response": "".join(content),
        "reasoning": "".join(reasoning) or None,
        "finish_reason": finish_reason,
        "first_token_seconds": None if first is None else first - sent,
        "generation_seconds": None if first is None else last - first,
        "total_seconds": done - sent,
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
    }


def messages_for(case: dict[str, Any]) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": case["system"]}] if case.get("system") else []
    return messages + [{"role": "user", "content": case["prompt"]}]


def run_once(
    endpoint: Endpoint,
    task: dict[str, Any],
    case: dict[str, Any],
    run_index: int,
    batch_id: str,
    commit: str | None,
    langfuse: Any,
) -> dict[str, Any]:
    spec = endpoint.spec
    started = datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "task_id": task["id"],
        "case_id": case["id"] if "source" in task else None,
        "model_id": spec["id"],
        "machine": spec["machine"],
        "family": spec["family"],
        "model": spec["model"],
        "run_index": run_index,
        "batch_id": batch_id,
        "started_at": started.isoformat(),
        "repo_commit": commit,
        "system_prompt": case.get("system"),
        "prompt": case["prompt"],
        "ideal": case.get("ideal"),
        "target_words": task.get("target_words"),
        "max_tokens": task.get("max_tokens"),
    }

    def call() -> dict[str, Any]:
        result = stream_completion(endpoint, task, case)
        source = "server" if result["output_tokens"] is not None else "none"
        if source == "none" and endpoint.token_count_command:
            counted = count_tokens(endpoint.token_count_command, result["response"])
            if counted is not None:
                result["output_tokens"] = counted
                source = "count_command"
        result["token_count_source"] = source
        if result["output_tokens"] and result["generation_seconds"]:
            result["decode_tokens_per_second"] = result["output_tokens"] / result["generation_seconds"]
        result["word_count"] = len(result["response"].split())
        return result

    try:
        if langfuse is None:
            record.update(call())
        else:
            record.update(call_traced(langfuse, call, record, started))
    except Exception as exc:  # recorded in the result file rather than stopping the batch
        record["response"] = ""
        record["error"] = f"{type(exc).__name__}: {exc}"
    return {k: v for k, v in record.items() if v is not None}


def call_traced(langfuse: Any, call: Any, record: dict[str, Any], started: datetime) -> dict[str, Any]:
    """Call the model inside a Langfuse generation.

    A Langfuse failure never costs the run: it is written to `record["langfuse_error"]`, and if
    it happened before the model was called, the model is called untraced instead. A model
    failure is re-raised so run_once records it as the run's error, next to any Langfuse error.
    """
    from langfuse import propagate_attributes

    outcome: dict[str, Any] = {}
    try:
        with propagate_attributes(
            session_id=record["batch_id"],
            tags=[record["task_id"], record["model_id"], record["family"]],
            trace_name=f"{record['task_id']}:{record['model_id']}",
        ):
            with langfuse.start_as_current_observation(
                as_type="generation",
                name=record["task_id"],
                model=record["model"],
                input=messages_for({"system": record.get("system_prompt"), "prompt": record["prompt"]}),
                metadata={k: record[k] for k in ("model_id", "machine", "family", "run_index", "repo_commit")},
            ) as generation:
                try:
                    outcome["result"] = call()
                except Exception as exc:
                    outcome["model_error"] = exc
                    generation.update(level="ERROR", status_message=f"{type(exc).__name__}: {exc}")
                else:
                    result = outcome["result"]
                    usage = {
                        k: v
                        for k, v in (("input", result.get("input_tokens")), ("output", result.get("output_tokens")))
                        if v is not None
                    }
                    first = result.get("first_token_seconds")
                    generation.update(
                        output=result["response"],
                        usage_details=usage or None,
                        completion_start_time=None if first is None else started + timedelta(seconds=first),
                        metadata={"reasoning": result.get("reasoning"), "finish_reason": result.get("finish_reason")},
                    )
                    result["langfuse_trace_id"] = langfuse.get_current_trace_id()
    except Exception as exc:
        outcome["langfuse_error"] = f"{type(exc).__name__}: {exc}"

    # Written onto the record itself, so it survives even when the model error is re-raised below.
    if "langfuse_error" in outcome:
        record["langfuse_error"] = outcome["langfuse_error"]
    if "model_error" in outcome:
        raise outcome["model_error"]
    result = outcome.get("result")
    if result is None:  # Langfuse failed before the model was called
        result = call()
    return result


def langfuse_client() -> Any:
    """Return a Langfuse client if keys are in the environment, else None."""
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return None
    from langfuse import get_client

    return get_client()


def write_record(record: dict[str, Any]) -> Path:
    prefix = f"{record['case_id']}-" if record.get("case_id") else ""
    name = f"{prefix}{record['model_id']}-run{record['run_index']}.yaml"
    path = RUNS_DIR / record["task_id"] / record["batch_id"] / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True, width=100))
    return path

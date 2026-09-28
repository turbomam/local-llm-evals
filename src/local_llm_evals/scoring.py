"""Score run files: checks that need no judge, then one judge model from another family.

The judge is asked for JSON, and its reply is validated before anything is recorded. An
invalid reply gets one retry; after that the score file records a scoring_error and leaves
the judged fields out. A score is never filled in when the judge did not give one.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from local_llm_evals import runner

JUDGES_FILE = runner.REPO_ROOT / "config" / "judges.yaml"
JUDGE_PROMPTS_DIR = runner.REPO_ROOT / "judges"
SCORES_DIR = runner.REPO_ROOT / "results" / "scores"


class InvalidJudgment(ValueError):
    """The judge's reply was not the JSON object the prompt asked for."""


def load_judge_prompt(name: str) -> dict[str, Any]:
    return yaml.safe_load((JUDGE_PROMPTS_DIR / f"{name}.yaml").read_text())


def choose_judge(
    generator_family: str, judges: list[dict[str, Any]], models: dict[str, dict[str, Any]]
) -> tuple[runner.Endpoint, str] | str:
    """Return (endpoint, status) for the first runnable judge outside the generator's family,
    or a string saying why none qualified."""
    reasons = []
    for judge in judges:
        spec = models.get(judge["model_id"])
        if spec is None:
            reasons.append(f"{judge['model_id']}: not in config/models.yaml")
            continue
        if spec["family"] == generator_family:
            reasons.append(f"{judge['model_id']}: same family as the generator ({generator_family})")
            continue
        resolved = runner.resolve(spec)
        if isinstance(resolved, str):
            reasons.append(f"{judge['model_id']}: {resolved}")
            continue
        return resolved, judge["status"]
    return "no eligible judge; " + "; ".join(reasons)


def build_messages(
    task: dict[str, Any], prompt: dict[str, Any], response: str, question: str | None = None
) -> list[dict[str, str]]:
    """question is the prompt the run actually received; it defaults to the task's current one."""
    checklist = "\n".join(f"{i}. {item}" for i, item in enumerate(task["checklist"], start=1))
    anchors = "\n".join(
        f"{name}:\n" + "\n".join(f"  {level}: {text}" for level, text in sorted(levels.items(), reverse=True))
        for name, levels in prompt["anchors"].items()
    )
    user = (
        f"Question:\n{question or task['prompt']}\n\n"
        f"Checklist ({len(task['checklist'])} items):\n{checklist}\n\n"
        f"Anchors:\n{anchors}\n\n"
        # JSON-encoded, so nothing in the answer can close the field and step outside it.
        f"Answer to grade, as JSON:\n{json.dumps({'answer': response}, ensure_ascii=False)}"
    )
    return [{"role": "system", "content": prompt["instructions"]}, {"role": "user", "content": user}]


def extract_json(text: str) -> Any:
    """Parse a JSON object, tolerating a code fence or text around it."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    elif "{" in text and "}" in text:
        candidate = text[text.find("{") : text.rfind("}") + 1]
    else:
        raise InvalidJudgment("no JSON object in the reply")
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise InvalidJudgment(f"not JSON: {exc}") from exc


def validate_judgment(data: Any, checklist_length: int) -> dict[str, Any]:
    """Check the judge's reply has every key, with the right types and ranges."""
    if not isinstance(data, dict):
        raise InvalidJudgment("reply is not a JSON object")
    items = data.get("checklist")
    if not isinstance(items, list) or len(items) != checklist_length:
        raise InvalidJudgment(f"checklist must be a list of {checklist_length} entries")
    for entry in items:
        if not isinstance(entry, dict) or not isinstance(entry.get("present"), bool):
            raise InvalidJudgment("each checklist entry needs a boolean 'present'")
        evidence = entry.get("evidence", "")
        if not isinstance(evidence, str):
            raise InvalidJudgment("checklist 'evidence' must be a string")
        if entry["present"] and not evidence.strip():
            raise InvalidJudgment("a checklist item marked present needs a quote as 'evidence'")
    statements = data.get("false_statements")
    if not isinstance(statements, list) or not all(
        isinstance(s, dict) and nonempty(s.get("quote")) and nonempty(s.get("why")) for s in statements
    ):
        raise InvalidJudgment("false_statements must be a list of objects with non-empty 'quote' and 'why'")
    for name in ("relevancy", "coherence"):
        value = data.get(name)
        score = value.get("score") if isinstance(value, dict) else None
        if type(score) is not int or score not in (1, 2, 3):  # rejects bools and floats like 1.0
            raise InvalidJudgment(f"{name}.score must be 1, 2 or 3")
        if not nonempty(value.get("reason")):
            raise InvalidJudgment(f"{name}.reason must be a non-empty string")
    return data


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def ask_judge(
    endpoint: runner.Endpoint, messages: list[dict[str, str]], max_tokens: int, checklist_length: int
) -> dict[str, Any]:
    """Call the judge; on an invalid reply, retry once with the error, then give up."""
    from openai import OpenAI

    client = OpenAI(base_url=endpoint.base_url, api_key=endpoint.api_key, timeout=1800)
    conversation = list(messages)
    last_error = None
    for _ in range(2):
        reply = client.chat.completions.create(
            model=endpoint.spec["model"], messages=conversation, max_tokens=max_tokens
        )
        text = reply.choices[0].message.content or ""
        try:
            return validate_judgment(extract_json(text), checklist_length)
        except InvalidJudgment as exc:
            last_error = exc
            conversation += [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"That reply was invalid ({exc}). Return only the JSON object."},
            ]
    raise InvalidJudgment(f"invalid after one retry: {last_error}")


def checklist_hash(task: dict[str, Any]) -> str:
    """Identifies the checklist a score was made against, so editing it triggers a rescore."""
    return hashlib.sha256(json.dumps(task["checklist"]).encode()).hexdigest()[:12]


def unjudged_scores(run: dict[str, Any], task: dict[str, Any], run_file: Path) -> dict[str, Any]:
    words = run.get("word_count", len(run.get("response", "").split()))
    # Prefer the target recorded with the run. Older runs lack it; for those the task's current
    # target is used only if the run was asked the task's current prompt, and otherwise no ratio
    # is recorded rather than one against a length the model was never asked to meet.
    if "target_words" in run:
        target = run["target_words"]
    elif run.get("prompt", task["prompt"]) == task["prompt"]:
        target = task.get("target_words")
    else:
        target = None
    return {
        "task_id": run["task_id"],
        "model_id": run["model_id"],
        "family": run["family"],
        "run_index": run["run_index"],
        "batch_id": run["batch_id"],
        "run_file": str(run_file.relative_to(runner.REPO_ROOT)),
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "word_count": words,
        "target_words": target,
        "word_count_ratio": round(words / target, 3) if target else None,
        "finished": run.get("finish_reason") == "stop",
        "empty_response": not run.get("response", "").strip(),
        "checklist_hash": checklist_hash(task),
    }


def add_judgment(scores: dict[str, Any], judgment: dict[str, Any], task: dict[str, Any]) -> None:
    scores["checklist"] = [
        # Evidence is kept only for present items; a quote beside an absent item would read as support.
        clean({"item": item, "present": entry["present"], "evidence": (entry.get("evidence") or None) if entry["present"] else None})
        for item, entry in zip(task["checklist"], judgment["checklist"])
    ]
    scores["checklist_present"] = sum(entry["present"] for entry in judgment["checklist"])
    scores["checklist_total"] = len(task["checklist"])
    scores["false_statements"] = [
        clean({"quote": s["quote"], "why": s.get("why") or None}) for s in judgment["false_statements"]
    ]
    scores["false_statement_count"] = len(judgment["false_statements"])
    for name in ("relevancy", "coherence"):
        scores[name] = judgment[name]["score"]
        scores[f"{name}_reason"] = judgment[name].get("reason")


def score_run(
    run_file: Path,
    task: dict[str, Any],
    judges: list[dict[str, Any]],
    models: dict[str, dict[str, Any]],
    ask: Any = ask_judge,
) -> dict[str, Any]:
    run = yaml.safe_load(run_file.read_text())
    scores = unjudged_scores(run, task, run_file)
    if run.get("error"):
        scores["scoring_error"] = f"run failed: {run['error']}"
        return clean(scores)
    if scores["empty_response"]:
        scores["scoring_error"] = "empty response; nothing to judge"
        return clean(scores)

    chosen = choose_judge(run["family"], judges, models)
    if isinstance(chosen, str):
        scores["scoring_error"] = chosen
        return clean(scores)
    endpoint, status = chosen
    prompt = load_judge_prompt(task["judge_prompt"])
    scores.update(
        judge_model_id=endpoint.spec["id"],
        judge_family=endpoint.spec["family"],
        judge_status=status,
        judge_prompt_version=prompt["version"],
    )
    started = time.perf_counter()
    try:
        judgment = ask(
            endpoint,
            build_messages(task, prompt, run["response"], run.get("prompt")),
            prompt.get("max_tokens", 8192),
            len(task["checklist"]),
        )
    except Exception as exc:  # recorded, never replaced by a made-up score
        scores["scoring_error"] = f"{type(exc).__name__}: {exc}"
    else:
        add_judgment(scores, judgment, task)
    scores["judge_seconds"] = round(time.perf_counter() - started, 2)
    return clean(scores)


UNJUDGED_NUMERIC = ("word_count", "word_count_ratio")
UNJUDGED_BOOLEAN = ("finished", "empty_response")
JUDGED_NUMERIC = ("checklist_present", "false_statement_count", "relevancy", "coherence")


def score_id(trace_id: str, name: str) -> str:
    """One id per trace and metric, whichever judge or prompt produced the value.

    Langfuse overwrites a score only when id, name and timestamp date all match, so a rescore
    reuses this id and the run's start date to replace the old value instead of adding a
    second one under the same metric name.
    """
    return hashlib.sha256(f"{trace_id}:{name}".encode()).hexdigest()[:32]


def send_to_langfuse(
    langfuse: Any, trace_id: str | None, scores: dict[str, Any], timestamp: datetime | None = None
) -> bool:
    """Queue the run's scores on its trace. Returns True if every score was queued.

    Queuing is not delivery: the caller marks scores as sent only after a successful flush.
    A queuing failure is recorded in `langfuse_error`, not raised. The checks that need no
    judge are sent for every scored run; the judged scores only when the judge gave them.
    """
    if langfuse is None or not trace_id:
        return False

    def send(name: str, value: float, data_type: str, comment: str | None = None) -> None:
        langfuse.create_score(
            name=name,
            value=value,
            trace_id=trace_id,
            data_type=data_type,
            comment=comment,
            score_id=score_id(trace_id, name),
            timestamp=timestamp,
        )

    try:
        for name in UNJUDGED_NUMERIC:
            if name in scores:
                send(name, float(scores[name]), "NUMERIC")
        for name in UNJUDGED_BOOLEAN:
            if name in scores:
                send(name, 1.0 if scores[name] else 0.0, "BOOLEAN")
        if "checklist_present" in scores:
            comment = (
                f"judge {scores['judge_model_id']} ({scores['judge_status']}), "
                f"prompt {scores['judge_prompt_version']}"
            )
            for name in JUDGED_NUMERIC:
                send(name, float(scores[name]), "NUMERIC", comment)
    except Exception as exc:
        scores["langfuse_error"] = f"{type(exc).__name__}: {exc}"
        return False
    scores.pop("langfuse_error", None)
    return True


def flush_and_mark(langfuse: Any, queued: list[dict[str, Any]]) -> str | None:
    """Flush queued scores; only if the flush succeeds, mark them sent and rewrite their files.

    Returns None on success, or the flush error. On failure nothing is marked, so the next run
    finds the cached scores unsent and queues them again.
    """
    try:
        langfuse.flush()
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    for scores in queued:
        scores["langfuse_sent"] = True
        write_scores(scores)
    return None


def run_timestamp(run: dict[str, Any]) -> datetime | None:
    """The run's start time, used as the score timestamp so a rescore keeps the same date."""
    started = run.get("started_at")
    if isinstance(started, datetime):
        return started
    return datetime.fromisoformat(started) if started else None


def needs_retry(
    existing: dict[str, Any], prompt_version: str | None = None, checklist: str | None = None
) -> bool:
    """Whether to run the judge again: only if the judge failed, or its prompt or the task's
    checklist has changed.

    A Langfuse delivery failure is not a reason to rejudge; the cached scores are resent
    instead, because they lack langfuse_sent. A run that failed or gave an empty response is
    recorded with no judge and is not retried: its outcome is fixed."""
    if "judge_model_id" not in existing:
        return False
    if prompt_version and existing.get("judge_prompt_version") != prompt_version:
        return True
    if checklist and existing.get("checklist_hash") != checklist:
        return True
    return "scoring_error" in existing


def expected_judge_id(
    run: dict[str, Any], judges: list[dict[str, Any]], models: dict[str, dict[str, Any]]
) -> str:
    """The judge a fresh scoring of this run would use, or "no-judge", matching score_path."""
    if run.get("error") or not run.get("response", "").strip():
        return "no-judge"
    chosen = choose_judge(run["family"], judges, models)
    return "no-judge" if isinstance(chosen, str) else chosen[0].spec["id"]


def score_path(scores: dict[str, Any]) -> Path:
    judge = scores.get("judge_model_id", "no-judge")
    return (
        SCORES_DIR
        / scores["task_id"]
        / scores["batch_id"]
        / f"{scores['model_id']}-run{scores['run_index']}.{judge}.yaml"
    )


def write_scores(scores: dict[str, Any]) -> Path:
    path = score_path(scores)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(scores, sort_keys=False, allow_unicode=True, width=100))
    return path


def clean(scores: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in scores.items() if v is not None}

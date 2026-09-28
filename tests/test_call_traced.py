"""A Langfuse failure must never cost a run's answer; a model failure must still surface."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

from local_llm_evals.runner import call_traced

STARTED = datetime.now(timezone.utc)


def new_record() -> dict:
    return {
        "batch_id": "b",
        "task_id": "t",
        "model_id": "m",
        "family": "f",
        "model": "x",
        "prompt": "p",
        "machine": "mc",
        "run_index": 1,
        "repo_commit": "c",
    }


class FakeGeneration:
    def __init__(self, fail_update: bool) -> None:
        self.fail_update = fail_update

    def update(self, **kwargs) -> None:
        if self.fail_update:
            raise RuntimeError("update failed")


class FakeLangfuse:
    def __init__(self, fail_start: bool = False, fail_update: bool = False) -> None:
        self.fail_start = fail_start
        self.fail_update = fail_update

    @contextmanager
    def start_as_current_observation(self, **kwargs):
        if self.fail_start:
            raise RuntimeError("start failed")
        yield FakeGeneration(self.fail_update)

    def get_current_trace_id(self) -> str:
        return "trace-1"


def counting_call(calls: list[int]):
    def call():
        calls.append(1)
        return {"response": "answer", "input_tokens": 1, "output_tokens": 2}

    return call


def failing_call():
    raise ConnectionError("model down")


def test_traced_run_keeps_answer_and_trace_id():
    calls: list[int] = []
    record = new_record()
    result = call_traced(FakeLangfuse(), counting_call(calls), record, STARTED)
    assert result["response"] == "answer"
    assert result["langfuse_trace_id"] == "trace-1"
    assert "langfuse_error" not in record
    assert len(calls) == 1


def test_langfuse_failure_after_answer_keeps_answer():
    calls: list[int] = []
    record = new_record()
    result = call_traced(FakeLangfuse(fail_update=True), counting_call(calls), record, STARTED)
    assert result["response"] == "answer"
    assert record["langfuse_error"] == "RuntimeError: update failed"
    assert len(calls) == 1


def test_langfuse_failure_before_call_runs_model_untraced():
    calls: list[int] = []
    record = new_record()
    result = call_traced(FakeLangfuse(fail_start=True), counting_call(calls), record, STARTED)
    assert result["response"] == "answer"
    assert record["langfuse_error"] == "RuntimeError: start failed"
    assert len(calls) == 1


def test_model_failure_is_reraised():
    with pytest.raises(ConnectionError, match="model down"):
        call_traced(FakeLangfuse(), failing_call, new_record(), STARTED)


def test_model_and_langfuse_failures_both_kept():
    record = new_record()
    with pytest.raises(ConnectionError, match="model down"):
        call_traced(FakeLangfuse(fail_update=True), failing_call, record, STARTED)
    assert record["langfuse_error"] == "RuntimeError: update failed"


def test_untraced_fallback_failure_keeps_langfuse_error():
    record = new_record()
    with pytest.raises(ConnectionError, match="model down"):
        call_traced(FakeLangfuse(fail_start=True), failing_call, record, STARTED)
    assert record["langfuse_error"] == "RuntimeError: start failed"

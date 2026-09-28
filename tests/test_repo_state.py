"""The runner must say when the recorded commit alone cannot reproduce a run."""

from __future__ import annotations

import subprocess

from local_llm_evals import runner


def _repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for key, value in (("user.email", "t@example.invalid"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", key, value], check=True)
    (tmp_path / "code.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "code.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "c"], check=True)


def test_clean_tree_is_not_dirty(tmp_path, monkeypatch) -> None:
    _repo(tmp_path)
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    assert runner.repo_dirty() is False


def test_edited_code_is_dirty(tmp_path, monkeypatch) -> None:
    _repo(tmp_path)
    (tmp_path / "code.py").write_text("x = 2\n")
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    assert runner.repo_dirty() is True


def test_new_results_do_not_count_as_dirty(tmp_path, monkeypatch) -> None:
    _repo(tmp_path)
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "r.yaml").write_text("a: 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "results/r.yaml"], check=True)
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    assert runner.repo_dirty() is False

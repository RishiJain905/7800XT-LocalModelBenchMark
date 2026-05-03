from __future__ import annotations

import json
from pathlib import Path

import pytest

from runners.resume import (
    completed_attempt_key,
    list_resumable_runs,
    load_resume_state,
    read_raw_results,
)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _make_run_dir(tmp_path: Path, status: str = "cancelled") -> Path:
    run_dir = tmp_path / "results" / "runs" / "model-1" / "run-1"
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "manifest.json",
        {
            "run_id": "run-1",
            "model_config_id": "model-1",
            "model_name": "Model One",
            "task_file": str(tmp_path / "tasks.jsonl"),
            "status": status,
            "repeats": 2,
            "suite_id": "reasoning.math",
            "suite_name": "Math",
            "server_url": "http://127.0.0.1:8080/v1/chat/completions",
            "settings": {"temperature": 0, "top_p": 1, "max_tokens": 128},
        },
    )
    (run_dir / "raw.jsonl").touch()
    return run_dir


def test_read_raw_results_parses_valid_lines_and_skips_blank_lines(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "raw.jsonl").write_text(
        json.dumps({"task_id": "t1", "repeat_index": 0}) + "\n\n"
        + json.dumps({"task_id": "t2", "repeat_index": 1}) + "\n",
        encoding="utf-8",
    )

    results, warnings = read_raw_results(run_dir)

    assert [result["task_id"] for result in results] == ["t1", "t2"]
    assert warnings == []


def test_read_raw_results_reports_corrupted_lines_in_non_strict_mode(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "raw.jsonl").write_text(
        json.dumps({"task_id": "t1", "repeat_index": 0}) + "\n{bad json\n",
        encoding="utf-8",
    )

    results, warnings = read_raw_results(run_dir)

    assert [result["task_id"] for result in results] == ["t1"]
    assert len(warnings) == 1
    assert "line 2" in warnings[0]


def test_read_raw_results_raises_on_corrupted_lines_in_strict_mode(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "raw.jsonl").write_text("{bad json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="raw.jsonl line 1"):
        read_raw_results(run_dir, strict=True)


def test_completed_attempt_key_requires_task_id_and_repeat_index():
    assert completed_attempt_key({"task_id": "t1", "repeat_index": 2}) == ("t1", 2)
    assert completed_attempt_key({"task_id": "t1"}) is None
    assert completed_attempt_key({"repeat_index": 0}) is None


def test_load_resume_state_builds_completed_keys_and_warns_for_bad_records(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    _write_jsonl(
        tmp_path / "tasks.jsonl",
        [
            {
                "id": "t1",
                "description": "Q1",
                "command": "noop",
                "expected_output": "A1",
                "metadata": {"category": "text"},
            },
            {
                "id": "t2",
                "description": "Q2",
                "command": "noop",
                "expected_output": "A2",
                "metadata": {"category": "text"},
            },
        ],
    )
    _write_jsonl(
        run_dir / "raw.jsonl",
        [
            {"task_id": "t1", "repeat_index": 0, "passed": True},
            {"task_id": "missing-repeat", "passed": True},
        ],
    )

    state = load_resume_state(run_dir)

    assert state.run_dir == run_dir.resolve()
    assert state.repeats == 2
    assert state.total_attempts == 4
    assert state.completed_attempts == {("t1", 0)}
    assert [task["id"] for task in state.tasks] == ["t1", "t2"]
    assert state.suite_info == {"id": "reasoning.math", "name": "Math"}
    assert any("missing task_id or repeat_index" in warning for warning in state.warnings)


def test_load_resume_state_infers_repeats_from_raw_repeat_count(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    del manifest["repeats"]
    _write_json(run_dir / "manifest.json", manifest)
    _write_jsonl(
        tmp_path / "tasks.jsonl",
        [
            {
                "id": "t1",
                "description": "Q1",
                "command": "noop",
                "expected_output": "A1",
                "metadata": {"category": "text"},
            }
        ],
    )
    _write_jsonl(
        run_dir / "raw.jsonl",
        [{"task_id": "t1", "repeat_index": 0, "repeat_count": 3, "passed": True}],
    )

    state = load_resume_state(run_dir)

    assert state.repeats == 3
    assert state.total_attempts == 3


def test_list_resumable_runs_includes_incomplete_statuses_only(tmp_path):
    root = tmp_path / "results" / "runs"
    statuses = ["running", "cancelled", "failed", "completed"]
    for status in statuses:
        run_dir = root / "model-1" / status
        run_dir.mkdir(parents=True)
        _write_json(
            run_dir / "manifest.json",
            {
                "run_id": status,
                "model_config_id": "model-1",
                "task_file": "tasks.jsonl",
                "status": status,
            },
        )

    resumable = list_resumable_runs(root)

    assert [item["status"] for item in resumable] == ["cancelled", "failed", "running"]
    assert all(item["run_dir"].endswith(item["run_id"]) for item in resumable)

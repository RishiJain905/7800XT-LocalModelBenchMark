"""Tests for structured run storage helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runners.result_writer import (
    append_run_raw_result,
    build_manifest,
    create_run_folder,
    sanitize_filename,
    save_artifact,
    update_manifest_status,
    write_manifest,
    write_run_raw_results,
    write_run_summary,
)


def _make_config() -> dict:
    return {
        "id": "model-1",
        "model_name": "Model One",
        "runtime": {"server_url": "http://127.0.0.1:8080/v1/chat/completions"},
        "settings": {
            "context_size": 4096,
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 256,
        },
    }


def test_create_run_folder_creates_required_structure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    run_dir = create_run_folder("model-1", "run-1")

    assert run_dir == tmp_path / "results" / "runs" / "model-1" / "run-1"
    assert run_dir.exists()
    assert (run_dir / "artifacts").is_dir()


def test_manifest_write_and_status_update(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    run_dir = create_run_folder("model-1", "run-1")
    manifest = build_manifest(
        _make_config(),
        "benchmarks/reasoning/math.jsonl",
        "run-1",
        "running",
        "2026-05-03T12:00:00",
        suite_info={"id": "reasoning.math", "name": "Math"},
    )

    manifest_path = write_manifest(run_dir, manifest)
    update_manifest_status(run_dir, "completed", "2026-05-03T12:05:00")

    assert manifest_path == str((run_dir / "manifest.json").resolve())
    data = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert data["run_id"] == "run-1"
    assert data["model_config_id"] == "model-1"
    assert data["model_name"] == "Model One"
    assert data["suite_id"] == "reasoning.math"
    assert data["suite_name"] == "Math"
    assert data["task_file"] == "benchmarks/reasoning/math.jsonl"
    assert data["server_url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert data["settings"]["max_tokens"] == 256
    assert data["status"] == "completed"
    assert data["started_at"] == "2026-05-03T12:00:00"
    assert data["completed_at"] == "2026-05-03T12:05:00"


def test_update_manifest_status_rejects_invalid_status(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    run_dir = create_run_folder("model-1", "run-1")
    write_manifest(
        run_dir,
        build_manifest(_make_config(), "tasks.jsonl", "run-1", "running", "start"),
    )

    with pytest.raises(ValueError, match="Invalid run status"):
        update_manifest_status(run_dir, "paused")


def test_raw_results_and_summary_are_written(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    run_dir = create_run_folder("model-1", "run-1")
    results = [
        {
            "task_id": "t1",
            "latency_sec": 0.5,
            "score": 1.0,
            "passed": True,
            "artifact_paths": ["artifacts/suite/t1_response.py"],
        },
        {
            "task_id": "t2",
            "latency_sec": 1.5,
            "score": 0.0,
            "passed": False,
            "artifact_paths": [],
        },
    ]
    summary = {
        "run_id": "run-1",
        "total_tasks": 2,
        "total_attempts": 2,
        "passed": 1,
        "failed": 1,
        "average_score": 0.5,
        "average_latency_sec": 1.0,
        "results": results,
    }

    raw_path = write_run_raw_results(run_dir, results)
    summary_path = write_run_summary(
        run_dir,
        summary,
        _make_config(),
        "tasks.jsonl",
        "completed",
        repeats=1,
        suite_info={"id": "reasoning.math", "name": "Math"},
        started_at="2026-05-03T12:00:00",
        completed_at="2026-05-03T12:05:00",
    )

    raw_lines = (run_dir / "raw.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert raw_path == str((run_dir / "raw.jsonl").resolve())
    assert len(raw_lines) == 2
    assert json.loads(raw_lines[0])["task_id"] == "t1"

    data = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary_path == str((run_dir / "summary.json").resolve())
    assert data["run_id"] == "run-1"
    assert data["model_config_id"] == "model-1"
    assert data["model_name"] == "Model One"
    assert data["suite_id"] == "reasoning.math"
    assert data["suite_name"] == "Math"
    assert data["task_file"] == "tasks.jsonl"
    assert data["run_folder"] == str(run_dir)
    assert data["status"] == "completed"
    assert data["total_tasks"] == 2
    assert data["total_attempts"] == 2
    assert data["passed"] == 1
    assert data["failed"] == 1
    assert data["pass_rate"] == 0.5
    assert data["average_score"] == 0.5
    assert data["average_latency_sec"] == 1.0
    assert data["repeats"] == 1
    assert data["artifact_count"] == 1
    assert data["started_at"] == "2026-05-03T12:00:00"
    assert data["completed_at"] == "2026-05-03T12:05:00"


def test_append_run_raw_result_appends_readable_jsonl(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    run_dir = create_run_folder("model-1", "run-1")

    first_path = append_run_raw_result(run_dir, {"task_id": "t1", "score": 1.0})
    second_path = append_run_raw_result(run_dir, {"task_id": "t2", "score": 0.0})

    assert first_path == str((run_dir / "raw.jsonl").resolve())
    assert second_path == first_path

    lines = (run_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["task_id"] for line in lines] == ["t1", "t2"]


def test_append_run_raw_result_flushes_and_fsyncs(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    run_dir = create_run_folder("model-1", "run-1")
    fsync_calls: list[int] = []

    def fake_fsync(fd: int) -> None:
        fsync_calls.append(fd)

    monkeypatch.setattr("runners.result_writer.os.fsync", fake_fsync)

    append_run_raw_result(run_dir, {"task_id": "t1"})

    assert len(fsync_calls) == 1
    assert json.loads((run_dir / "raw.jsonl").read_text(encoding="utf-8")) == {
        "task_id": "t1"
    }


def test_sanitize_filename():
    assert sanitize_filename("hello_world") == "hello_world"
    assert sanitize_filename("hello world!") == "hello_world_"
    assert sanitize_filename("a/b/c") == "a_b_c"
    assert sanitize_filename("valid-name.ext") == "valid-name.ext"


def test_save_artifact_default_extension(tmp_path):
    task = {"id": "my_task", "metadata": {"category": "code"}}
    response = "console.log('hello');"

    path = save_artifact(tmp_path, "coding.frontend", task, response)

    expected_file = tmp_path / "artifacts" / "coding.frontend" / "my_task_response.md"
    assert expected_file.exists()
    assert expected_file.read_text(encoding="utf-8") == response
    assert path == str(expected_file.resolve())


def test_save_artifact_custom_extension(tmp_path):
    task = {
        "id": "api_handler_001",
        "metadata": {"category": "code", "artifact_extension": ".py"},
    }
    response = "def handler(): pass"

    path = save_artifact(tmp_path, "coding.backend", task, response)

    expected_file = (
        tmp_path / "artifacts" / "coding.backend" / "api_handler_001_response.py"
    )
    assert expected_file.exists()
    assert expected_file.read_text(encoding="utf-8") == response
    assert path == str(expected_file.resolve())


def test_save_artifact_returns_absolute_path(tmp_path):
    task = {"id": "abs_task", "metadata": {"category": "code"}}
    response = "print('hello')"

    path = save_artifact(tmp_path, "suite.a", task, response)

    assert isinstance(path, str)
    assert Path(path).is_absolute()
    assert Path(path).exists()


def test_save_artifact_with_special_chars_in_id(tmp_path):
    task = {"id": "my task/123!", "metadata": {"category": "code"}}
    response = "some code"

    path = save_artifact(tmp_path, "suite.b", task, response)

    expected_file = tmp_path / "artifacts" / "suite.b" / "my_task_123__response.md"
    assert expected_file.exists()
    assert "/" not in expected_file.name
    assert "!" not in expected_file.name
    assert " " not in expected_file.name
    assert path == str(expected_file.resolve())

"""Comprehensive unit and integration tests for run_benchmark.py.

Tests cover helper functions in isolation and `main()` through
monkey-patching of external dependencies and `sys.argv`.
"""

from __future__ import annotations

import json
import os
import csv
import sys
from datetime import datetime
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
import yaml

from run_benchmark import main
from runners.benchmark_runner import (
    _build_error_result,
    _build_result,
    _extract_settings,
    _resolve_scorer,
)

from runners.leaderboard import generate_leaderboard
from runners.result_writer import append_summary, write_raw_results

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_task(
    task_id: str = "task-01",
    description: str = "Do something",
    category: str = "general",
    expected_output: str = "something",
) -> dict[str, Any]:
    """Return a minimal task dict suitable for the benchmark helpers."""
    task: dict[str, Any] = {
        "id": task_id,
        "description": description,
        "command": description,
        "expected_output": expected_output,
    }
    if category is not None:
        task["metadata"] = {"category": category}
    return task


def _make_config(
    config_id: str = "test-config",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a minimal config dict."""
    if settings is None:
        settings = {
            "context_size": 4096,
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 1024,
        }
    return {
        "id": config_id,
        "model_name": "TestModel",
        "runtime": {"server_url": "http://127.0.0.1:8080/v1/chat/completions"},
        "settings": settings,
    }


def _make_model_result(
    response: str = "ok", latency_sec: float = 1.23
) -> dict[str, Any]:
    return {"response": response, "latency_sec": latency_sec}


def _make_score_result(
    score: float = 1.0, passed: bool = True, reason: str = "ok"
) -> dict[str, Any]:
    return {"score": score, "passed": passed, "reason": reason}


def _write_yaml(path: os.PathLike, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def _write_jsonl(path: os.PathLike, lines: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


@pytest.fixture
def sample_results() -> list[dict]:
    """Return a sample list of 3 result dicts (2 passed, 1 failed)."""
    return [
        {
            "run_id": "r1",
            "model_config_id": "cfg",
            "task_file": "t.jsonl",
            "task_id": "t1",
            "category": "text",
            "prompt": "q1",
            "response": "a1",
            "latency_sec": 0.5,
            "score": 1.0,
            "passed": True,
            "reason": "ok",
            "settings": {},
        },
        {
            "run_id": "r1",
            "model_config_id": "cfg",
            "task_file": "t.jsonl",
            "task_id": "t2",
            "category": "text",
            "prompt": "q2",
            "response": "a2",
            "latency_sec": 1.5,
            "score": 0.0,
            "passed": False,
            "reason": "wrong",
            "settings": {},
        },
        {
            "run_id": "r1",
            "model_config_id": "cfg",
            "task_file": "t.jsonl",
            "task_id": "t3",
            "category": "text",
            "prompt": "q3",
            "response": "a3",
            "latency_sec": 1.0,
            "score": 1.0,
            "passed": True,
            "reason": "ok",
            "settings": {},
        },
    ]


# ---------------------------------------------------------------------------
# _resolve_scorer
# ---------------------------------------------------------------------------


class TestResolveScorer:
    """Mapping from task metadata category to scorer name."""

    @pytest.mark.parametrize(
        ("category", "expected_scorer"),
        [
            ("math", "numeric_close"),
            ("numeric", "numeric_close"),
            ("text", "exact_match"),
            ("general", "exact_match"),
            ("keyword", "keyword_match"),
            ("code", "keyword_match"),
            ("json", "json_valid"),
            ("tool", "json_valid"),
        ],
    )
    def test_known_categories(self, category, expected_scorer):
        """Each category in CATEGORY_SCORER_MAP resolves correctly."""
        task = _make_task(category=category)
        assert _resolve_scorer(task) == expected_scorer

    def test_unknown_category_uses_fallback(self):
        """A category absent from the map falls back to exact_match."""
        task = _make_task(category="weird")
        assert _resolve_scorer(task) == "exact_match"

    def test_empty_string_category_uses_fallback(self):
        """Empty string category falls back to exact_match."""
        task = _make_task(category="")
        assert _resolve_scorer(task) == "exact_match"

    def test_missing_category_uses_fallback(self):
        """Missing category key inside metadata falls back."""
        task = _make_task(category="general")
        del task["metadata"]["category"]
        assert _resolve_scorer(task) == "exact_match"

    def test_missing_metadata_uses_fallback(self):
        """Missing metadata entirely falls back."""
        task = _make_task(category="general")
        del task["metadata"]
        assert _resolve_scorer(task) == "exact_match"


# ---------------------------------------------------------------------------
# _extract_settings
# ---------------------------------------------------------------------------


class TestExtractSettings:
    """Pull tracked settings out of a config dict."""

    def test_returns_all_keys_when_present(self):
        config = _make_config(
            settings={
                "context_size": 4096,
                "temperature": 0.0,
                "top_p": 1.0,
                "max_tokens": 1024,
            }
        )
        result = _extract_settings(config)
        assert result == {
            "context_size": 4096,
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 1024,
        }

    def test_returns_none_for_missing_keys(self):
        config = _make_config(settings={"temperature": 0.5})
        result = _extract_settings(config)
        assert result["temperature"] == 0.5
        assert result["context_size"] is None
        assert result["top_p"] is None
        assert result["max_tokens"] is None

    def test_returns_none_values_when_no_settings_key(self):
        config = _make_config()
        del config["settings"]
        result = _extract_settings(config)
        assert result == {
            "context_size": None,
            "temperature": None,
            "top_p": None,
            "max_tokens": None,
        }


# ---------------------------------------------------------------------------
# _build_result
# ---------------------------------------------------------------------------


class TestBuildResult:
    """Successful-run result dict construction."""

    def test_all_fields_present_and_mapped(self):
        task = _make_task(
            task_id="t-01",
            description="hello",
            category="text",
            expected_output="world",
        )
        config = _make_config(config_id="cfg-01")
        model_result = _make_model_result(response="model says hi", latency_sec=2.5)
        score_result = _make_score_result(score=0.75, passed=True, reason="close")
        run_id = "2025-01-01_12-00-00"

        result = _build_result(
            task, config, model_result, score_result, "tasks.jsonl", run_id
        )

        assert result["run_id"] == run_id
        assert result["model_config_id"] == "cfg-01"
        assert result["task_id"] == "t-01"
        assert result["category"] == "text"
        assert result["task_file"] == "tasks.jsonl"
        assert result["prompt"] == "hello"
        assert result["expected"] == "world"
        assert result["response"] == "model says hi"
        assert result["latency_sec"] == 2.5
        assert result["score"] == 0.75
        assert result["passed"] is True
        assert result["reason"] == "close"
        assert isinstance(result["settings"], dict)
        assert set(result["settings"].keys()) == {
            "context_size",
            "temperature",
            "top_p",
            "max_tokens",
        }


# ---------------------------------------------------------------------------
# _build_error_result
# ---------------------------------------------------------------------------


class TestBuildErrorResult:
    """Failed-run result dict construction."""

    def test_error_fields_are_set_correctly(self):
        task = _make_task(
            task_id="t-02", description="fail task", expected_output="n/a"
        )
        config = _make_config(config_id="cfg-02")
        error = "Connection refused"
        run_id = "2025-01-01_12-00-01"

        result = _build_error_result(task, config, error, "tasks.jsonl", run_id)

        # Error-specific assertions
        assert result["response"] == ""
        assert result["latency_sec"] == 0.0
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert result["reason"] == error

        # Remaining fields mirror _build_result shape
        assert result["run_id"] == run_id
        assert result["model_config_id"] == "cfg-02"
        assert result["task_id"] == "t-02"
        assert result["prompt"] == "fail task"
        assert result["expected"] == "n/a"
        assert isinstance(result["settings"], dict)


# ---------------------------------------------------------------------------
# write_raw_results
# ---------------------------------------------------------------------------


class TestWriteRawResults:
    """Writing raw benchmark results to JSONL files."""

    def test_creates_directory_and_writes_jsonl(
        self, monkeypatch, tmp_path, sample_results
    ):
        """Directory and JSONL file are created with one JSON object per line."""
        monkeypatch.chdir(tmp_path)
        path = write_raw_results(sample_results, "model-cfg", "tasks.jsonl", "run-1")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        assert len(lines) == len(sample_results)
        for line, expected in zip(lines, sample_results):
            assert json.loads(line) == expected

    def test_empty_results_list(self, monkeypatch, tmp_path):
        """An empty results list produces an empty file and still returns a path."""
        monkeypatch.chdir(tmp_path)
        path = write_raw_results([], "model-cfg", "tasks.jsonl", "run-1")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert content == ""

    def test_directory_structure(self, monkeypatch, tmp_path):
        """Correct nested directory is created under the current working directory."""
        monkeypatch.chdir(tmp_path)
        write_raw_results([], "my-model", "tasks.jsonl", "run-1")
        expected_dir = tmp_path / "results" / "raw" / "my-model"
        assert expected_dir.exists()
        assert expected_dir.is_dir()

    def test_stem_extraction(self, monkeypatch, tmp_path):
        """Filename stem is extracted from the task_file path."""
        monkeypatch.chdir(tmp_path)
        task_file = "/some/path/math/basic_math.jsonl"
        path = write_raw_results([], "model-cfg", task_file, "xyz")
        filename = os.path.basename(path)
        assert filename == "basic_math_xyz.jsonl"

    def test_returns_absolute_path(self, monkeypatch, tmp_path, sample_results):
        """Return value is an absolute path string."""
        monkeypatch.chdir(tmp_path)
        path = write_raw_results(sample_results, "model-cfg", "tasks.jsonl", "run-1")
        assert os.path.isabs(path)


# ---------------------------------------------------------------------------
# append_summary
# ---------------------------------------------------------------------------


class TestAppendSummary:
    """Appending benchmark summary rows to a CSV file."""

    def test_creates_csv_with_header(self, monkeypatch, tmp_path, sample_results):
        """When summary.csv does not exist, a header row is written first."""
        monkeypatch.chdir(tmp_path)
        append_summary(sample_results, "cfg", "tasks.jsonl", "run-1")
        summary_path = tmp_path / "results" / "summary.csv"
        assert summary_path.exists()
        with open(summary_path, encoding="utf-8") as f:
            content = f.read().strip().split("\n")
        assert len(content) == 2  # header + 1 data row
        header = content[0]
        assert header == (
            "run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,"
            "pass_rate,average_score,average_latency_sec,repeats,suite_id,suite_name,"
            "run_folder,status,started_at,completed_at,artifact_count"
        )

    def test_appends_row(self, monkeypatch, tmp_path):
        """Calling append_summary twice creates two data rows under one header."""
        monkeypatch.chdir(tmp_path)
        results1 = [{"latency_sec": 1.0, "score": 1.0, "passed": True}]
        results2 = [{"latency_sec": 2.0, "score": 0.0, "passed": False}]
        append_summary(results1, "cfg", "tasks.jsonl", "run-1")
        append_summary(results2, "cfg", "tasks.jsonl", "run-2")
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows
        assert "run-1" in lines[1]
        assert "run-2" in lines[2]

    def test_stats_computation_all_passed(self, monkeypatch, tmp_path):
        """All-passed results produce pass_rate=1.0, total_attempts=3, repeats=1."""
        monkeypatch.chdir(tmp_path)
        results = [
            {
                "latency_sec": 0.5,
                "score": 0.8,
                "passed": True,
                "repeat_index": 0,
                "repeat_count": 1,
            },
            {
                "latency_sec": 1.5,
                "score": 1.0,
                "passed": True,
                "repeat_index": 0,
                "repeat_count": 1,
            },
            {
                "latency_sec": 1.0,
                "score": 0.9,
                "passed": True,
                "repeat_index": 0,
                "repeat_count": 1,
            },
        ]
        append_summary(results, "cfg", "tasks.jsonl", "run-1", repeats=1, total_tasks=3)
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[3] == "3"  # total_tasks
        assert parts[4] == "3"  # total_attempts
        assert parts[5] == "3"  # passed
        assert parts[6] == "0"  # failed
        assert parts[7] == "1.0000"  # pass_rate
        assert float(parts[8]) == pytest.approx(0.9, abs=0.0001)  # average_score
        assert float(parts[9]) == pytest.approx(1.0, abs=0.001)  # average_latency_sec
        assert parts[10] == "1"  # repeats

    def test_stats_computation_some_failed(self, monkeypatch, tmp_path, sample_results):
        """Mixed-pass results produce correct pass_rate and averages with repeats."""
        monkeypatch.chdir(tmp_path)
        for r in sample_results:
            r["repeat_index"] = 0
            r["repeat_count"] = 1
        append_summary(
            sample_results, "cfg", "tasks.jsonl", "run-1", repeats=1, total_tasks=3
        )
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[3] == "3"  # total_tasks
        assert parts[4] == "3"  # total_attempts
        assert parts[5] == "2"  # passed
        assert parts[6] == "1"  # failed
        assert parts[7] == "0.6667"  # pass_rate
        assert float(parts[8]) == pytest.approx(0.6667, abs=0.0001)  # average_score
        assert float(parts[9]) == pytest.approx(1.000, abs=0.001)  # average_latency_sec
        assert parts[10] == "1"  # repeats

    def test_empty_results_list(self, monkeypatch, tmp_path):
        """Empty results produce zeroes across all summary columns including new fields."""
        monkeypatch.chdir(tmp_path)
        append_summary([], "cfg", "tasks.jsonl", "run-1", repeats=1, total_tasks=0)
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[3] == "0"  # total_tasks
        assert parts[4] == "0"  # total_attempts
        assert parts[5] == "0"  # passed
        assert parts[6] == "0"  # failed
        assert parts[7] == "0.0000"  # pass_rate
        assert parts[8] == "0.0000"  # average_score
        assert parts[9] == "0.000"  # average_latency_sec
        assert parts[10] == "1"  # repeats

    def test_float_formatting(self, monkeypatch, tmp_path):
        """pass_rate uses :.4f and average_latency_sec uses :.3f with new columns."""
        monkeypatch.chdir(tmp_path)
        results = [
            {
                "latency_sec": 1.23456,
                "score": 0.666666,
                "passed": True,
                "repeat_index": 0,
                "repeat_count": 1,
            },
            {
                "latency_sec": 1.23456,
                "score": 0.666666,
                "passed": False,
                "repeat_index": 0,
                "repeat_count": 1,
            },
        ]
        append_summary(results, "cfg", "tasks.jsonl", "run-1", repeats=1, total_tasks=2)
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[4] == "2"  # total_attempts
        assert parts[5] == "1"  # passed
        assert parts[6] == "1"  # failed
        assert parts[7] == "0.5000"  # pass_rate
        assert parts[8] == "0.6667"  # avg score
        assert parts[9] == "1.235"  # avg latency
        assert parts[10] == "1"  # repeats

    def test_append_summary_with_repeats(self, monkeypatch, tmp_path):
        """Direct test of append_summary with repeats=3 populates new columns correctly."""
        monkeypatch.chdir(tmp_path)
        results = [
            {
                "latency_sec": 0.5,
                "score": 1.0,
                "passed": True,
                "repeat_index": 0,
                "repeat_count": 3,
            },
            {
                "latency_sec": 0.5,
                "score": 1.0,
                "passed": True,
                "repeat_index": 1,
                "repeat_count": 3,
            },
            {
                "latency_sec": 0.5,
                "score": 1.0,
                "passed": True,
                "repeat_index": 2,
                "repeat_count": 3,
            },
            {
                "latency_sec": 1.0,
                "score": 0.0,
                "passed": False,
                "repeat_index": 0,
                "repeat_count": 3,
            },
            {
                "latency_sec": 1.0,
                "score": 0.0,
                "passed": False,
                "repeat_index": 1,
                "repeat_count": 3,
            },
            {
                "latency_sec": 1.0,
                "score": 0.0,
                "passed": False,
                "repeat_index": 2,
                "repeat_count": 3,
            },
        ]
        append_summary(results, "cfg", "tasks.jsonl", "run-1", repeats=3, total_tasks=2)
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[3] == "2"  # total_tasks
        assert parts[4] == "6"  # total_attempts
        assert parts[5] == "3"  # passed
        assert parts[6] == "3"  # failed
        assert parts[7] == "0.5000"  # pass_rate
        assert parts[10] == "3"  # repeats

    def test_append_summary_writes_task16_metadata(self, monkeypatch, tmp_path):
        """Task 16 metadata columns are populated for new summary rows."""
        monkeypatch.chdir(tmp_path)
        results = [
            {
                "latency_sec": 0.5,
                "score": 1.0,
                "passed": True,
                "artifact_paths": ["a.tsx", "b.css"],
            }
        ]

        append_summary(
            results,
            "cfg",
            "benchmarks/coding/frontend.jsonl",
            "run-1",
            repeats=1,
            total_tasks=1,
            suite_info={"id": "coding.frontend", "name": "Frontend Coding"},
            run_folder="results/runs/cfg/run-1",
            status="completed",
            started_at="2026-05-03T12:00:00",
            completed_at="2026-05-03T12:05:00",
        )

        with open(tmp_path / "results" / "summary.csv", newline="", encoding="utf-8") as fh:
            row = next(csv.DictReader(fh))

        assert row["suite_id"] == "coding.frontend"
        assert row["suite_name"] == "Frontend Coding"
        assert row["run_folder"] == "results/runs/cfg/run-1"
        assert row["status"] == "completed"
        assert row["started_at"] == "2026-05-03T12:00:00"
        assert row["completed_at"] == "2026-05-03T12:05:00"
        assert row["artifact_count"] == "2"


# ---------------------------------------------------------------------------
# Integration tests for main()
# ---------------------------------------------------------------------------


class TestMainArgumentErrors:
    """`main()` exits with usage errors when required args are missing or invalid."""

    def test_missing_config_argument(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["run_benchmark.py", "--task-file", "tasks.jsonl"]
        )
        with pytest.raises(SystemExit):
            main()

    def test_missing_task_file_argument(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["run_benchmark.py", "--config", "config.yaml"]
        )
        with pytest.raises(SystemExit):
            main()

    def test_config_file_not_found(self, monkeypatch, capsys):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                "/nonexistent/path/config.yaml",
                "--task-file",
                "tasks.jsonl",
            ],
        )
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "Error loading config" in captured.err

    def test_task_file_not_found(self, monkeypatch, tmp_path, capsys):
        config_path = tmp_path / "config.yaml"
        _write_yaml(config_path, _make_config())
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                "/nonexistent/tasks.jsonl",
            ],
        )
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "Error loading tasks" in captured.err

    def test_empty_task_file(self, monkeypatch, tmp_path, capsys):
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config())
        _write_jsonl(task_path, [])
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "No tasks found" in captured.err


class TestMainDryRun:
    """Dry-run mode prints inspection info without calling the model."""

    def test_dry_run_output(self, monkeypatch, tmp_path, capsys):
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="dry-run-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "What is 2+2?", "math", "4"),
                _make_task("t-02", "Say hello", "text", "hello"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
                "--dry-run",
            ],
        )

        with patch("runners.benchmark_runner.run_prompt") as mock_prompt:
            main()
            mock_prompt.assert_not_called()

        captured = capsys.readouterr()
        out = captured.out
        assert "Config: dry-run-cfg" in out
        assert "Tasks: 2" in out
        assert 't-01: "What is 2+2?" -> numeric_close' in out
        assert 't-02: "Say hello" -> exact_match' in out

    def test_dry_run_does_not_create_structured_run_folder(
        self, monkeypatch, tmp_path
    ):
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="dry-run-cfg"))
        _write_jsonl(task_path, [_make_task("t-01", "What is 2+2?", "math", "4")])
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
                "--dry-run",
            ],
        )

        main()

        assert not (tmp_path / "results" / "runs").exists()

    def test_repo_sample_task_file_dry_run_loads(self, monkeypatch, capsys):
        """The documented sample task file should load in dry-run mode."""
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                "configs/qwen-9b-q8-4k.yaml",
                "--task-file",
                "data/tasks/task_01.jsonl",
                "--dry-run",
            ],
        )

        main()

        captured = capsys.readouterr()
        assert "Config: qwen-9b-q8-4k" in captured.out
        assert "Tasks:" in captured.out


class TestMainFullRun:
    """Normal execution with mocked model and scorer."""

    def test_full_run_progress_and_summary(self, monkeypatch, tmp_path, capsys):
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="full-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
                _make_task("t-02", "Q2", "text", "a2"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                main()

        captured = capsys.readouterr()
        out = captured.out
        assert "[1/2] t-01 (repeat 1/1)" in out
        assert "[2/2] t-02 (repeat 1/1)" in out
        assert "Total tasks: 2 (repeats=1, total_attempts=2)" in out
        assert "Passed: 2" in out
        assert "Average score: 1.00" in out
        assert "Average latency: 0.50s" in out

    def test_full_run_creates_structured_run_files(
        self, monkeypatch, tmp_path, capsys
    ):
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="full-cfg"))
        _write_jsonl(task_path, [_make_task("t-01", "Q1", "text", "a1")])
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                main()

        run_root = tmp_path / "results" / "runs" / "full-cfg"
        run_dirs = list(run_root.iterdir())
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        raw_lines = (run_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))

        assert (run_dir / "artifacts").is_dir()
        assert manifest["status"] == "completed"
        assert manifest["model_config_id"] == "full-cfg"
        assert manifest["completed_at"] is not None
        assert len(raw_lines) == 1
        assert json.loads(raw_lines[0])["task_id"] == "t-01"
        assert summary["run_id"] == manifest["run_id"]
        assert summary["pass_rate"] == 1.0

        out = capsys.readouterr().out
        assert str(run_dir / "raw.jsonl") in out

    def test_top_level_run_failure_marks_manifest_failed(
        self, monkeypatch, tmp_path
    ):
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="fail-cfg"))
        _write_jsonl(task_path, [_make_task("t-01", "Q1", "text", "a1")])
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        with patch("run_benchmark.run_benchmark", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                main()

        run_root = tmp_path / "results" / "runs" / "fail-cfg"
        run_dir = next(run_root.iterdir())
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        assert manifest["completed_at"] is not None

    def test_keyboard_interrupt_preserves_completed_attempts_as_cancelled(
        self, monkeypatch, tmp_path, capsys
    ):
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="cancel-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
                _make_task("t-02", "Q2", "text", "a2"),
            ],
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        call_count = 0

        def fake_run_prompt(config, prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise KeyboardInterrupt
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch("run_benchmark.write_raw_results") as mock_raw_copy:
                    with patch("run_benchmark.append_summary") as mock_append_summary:
                        with patch("run_benchmark.generate_leaderboard") as mock_lb:
                            with pytest.raises(SystemExit) as exc_info:
                                main()

        assert exc_info.value.code == 130
        mock_raw_copy.assert_not_called()
        mock_append_summary.assert_called_once()
        mock_lb.assert_not_called()

        run_root = tmp_path / "results" / "runs" / "cancel-cfg"
        run_dir = next(run_root.iterdir())
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        raw_lines = (run_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))

        assert manifest["status"] == "cancelled"
        assert manifest["completed_at"] is not None
        assert len(raw_lines) == 1
        assert json.loads(raw_lines[0])["task_id"] == "t-01"
        assert summary["status"] == "cancelled"
        assert summary["total_tasks"] == 2
        assert summary["total_attempts"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 0
        assert summary["pass_rate"] == 0.5

        out = capsys.readouterr().out
        assert "Run cancelled" in out
        assert str(run_dir / "raw.jsonl") in out

    def test_error_handling_continues_to_next_task(self, monkeypatch, tmp_path, capsys):
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="err-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-ok", "OK task", "text", "ok"),
                _make_task("t-bad", "Bad task", "text", "bad"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        call_count = 0

        def fake_run_prompt(config, prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("model exploded")
            return _make_model_result(response="answer", latency_sec=0.25)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                main()

        captured = capsys.readouterr()
        out = captured.out
        assert "[1/2] t-ok (repeat 1/1)" in out
        assert "[2/2] t-bad (repeat 1/1)" in out
        assert "Total tasks: 2 (repeats=1, total_attempts=2)" in out
        assert "Passed: 1" in out
        assert "Average score: 0.50" in out
        assert "Average latency: 0.12s" in out

    def test_write_raw_results_is_called(self, monkeypatch, tmp_path):
        """Verify that write_raw_results and append_summary are invoked once."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="full-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch("run_benchmark.write_raw_results") as mock_write:
                    with patch("run_benchmark.append_summary") as mock_append:
                        main()
                        mock_write.assert_called_once()
                        mock_append.assert_called_once()

    def test_output_paths_are_printed(self, monkeypatch, tmp_path, capsys):
        """Verify that the raw results and summary paths are printed to stdout."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="full-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch(
                    "run_benchmark.write_raw_results", return_value="/fake/raw.jsonl"
                ):
                    with patch(
                        "run_benchmark.append_summary", return_value="/fake/summary.csv"
                    ):
                        main()

        captured = capsys.readouterr()
        out = captured.out
        assert "Saved raw results to" in out
        assert "Update summary at" in out

    def test_write_raw_results_error_handling(self, monkeypatch, tmp_path, capsys):
        """If write_raw_results raises OSError, an error is printed and benchmark continues."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="err-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch(
                    "run_benchmark.write_raw_results", side_effect=OSError("disk full")
                ):
                    with patch(
                        "run_benchmark.append_summary", return_value="/fake/summary.csv"
                    ) as mock_append:
                        main()
                        mock_append.assert_called_once()

        captured = capsys.readouterr()
        err = captured.err
        assert "Error writing raw results" in err

    def test_generate_leaderboard_is_called(self, monkeypatch, tmp_path):
        """Verify that generate_leaderboard is invoked once."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="full-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch("run_benchmark.write_raw_results"):
                    with patch("run_benchmark.append_summary"):
                        with patch("run_benchmark.generate_leaderboard") as mock_lb:
                            main()
                            mock_lb.assert_called_once()

    def test_leaderboard_path_is_printed(self, monkeypatch, tmp_path, capsys):
        """Verify that the leaderboard path is printed to stdout."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="full-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch(
                    "run_benchmark.write_raw_results", return_value="/fake/raw.jsonl"
                ):
                    with patch(
                        "run_benchmark.append_summary", return_value="/fake/summary.csv"
                    ):
                        with patch(
                            "run_benchmark.generate_leaderboard",
                            return_value="/fake/leaderboard.md",
                        ):
                            main()

        captured = capsys.readouterr()
        out = captured.out
        assert "Updated leaderboard at" in out
        assert "/fake/leaderboard.md" in out

    def test_generate_leaderboard_error_handling(self, monkeypatch, tmp_path, capsys):
        """If generate_leaderboard raises OSError, an error is printed and benchmark continues."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="err-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch(
                    "run_benchmark.write_raw_results", return_value="/fake/raw.jsonl"
                ):
                    with patch(
                        "run_benchmark.append_summary", return_value="/fake/summary.csv"
                    ):
                        with patch(
                            "run_benchmark.generate_leaderboard",
                            side_effect=OSError("disk full"),
                        ) as mock_lb:
                            main()
                            mock_lb.assert_called_once()

        captured = capsys.readouterr()
        err = captured.err
        assert "Error writing leaderboard" in err


class TestMainRepeats:
    """Execution with mocked model and scorer using --repeats flag."""

    def test_repeats_defaults_to_1(self, monkeypatch, tmp_path, capsys):
        """Same as full run but explicitly verify --repeats 1 produces 1 result per task."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="repeat-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
                _make_task("t-02", "Q2", "text", "a2"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
                "--repeats",
                "1",
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch("run_benchmark.write_raw_results") as mock_write:
                    main()
                    # 2 tasks x 1 repeat = 2 results
                    assert mock_write.call_count == 1
                    written_results = mock_write.call_args[0][0]
                    assert len(written_results) == 2
                    for r in written_results:
                        assert r["repeat_index"] == 0
                        assert r["repeat_count"] == 1

        captured = capsys.readouterr()
        out = captured.out
        assert "[1/2] t-01 (repeat 1/1)" in out
        assert "[2/2] t-02 (repeat 1/1)" in out
        assert "Total tasks: 2 (repeats=1, total_attempts=2)" in out

    def test_repeats_3_produces_correct_results(self, monkeypatch, tmp_path, capsys):
        """--repeats 3 produces 6 results with correct repeat_index values and progress."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="repeat3-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
                _make_task("t-02", "Q2", "text", "a2"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
                "--repeats",
                "3",
            ],
        )

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch("run_benchmark.write_raw_results") as mock_write:
                    main()
                    # 2 tasks x 3 repeats = 6 results
                    written_results = mock_write.call_args[0][0]
                    assert len(written_results) == 6
                    repeat_indices = [r["repeat_index"] for r in written_results]
                    repeat_counts = [r["repeat_count"] for r in written_results]
                    assert repeat_indices == [0, 1, 2, 0, 1, 2]
                    assert all(rc == 3 for rc in repeat_counts)

        captured = capsys.readouterr()
        out = captured.out
        assert "[1/6] t-01 (repeat 1/3)" in out
        assert "[2/6] t-01 (repeat 2/3)" in out
        assert "[3/6] t-01 (repeat 3/3)" in out
        assert "[4/6] t-02 (repeat 1/3)" in out
        assert "[5/6] t-02 (repeat 2/3)" in out
        assert "[6/6] t-02 (repeat 3/3)" in out
        assert "Total tasks: 2 (repeats=3, total_attempts=6)" in out

    def test_repeats_with_errors(self, monkeypatch, tmp_path, capsys):
        """Repeats with one error on 2nd task’s 2nd repeat still produce 6 results total."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="err-repeat-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-ok", "OK task", "text", "ok"),
                _make_task("t-bad", "Bad task", "text", "bad"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
                "--repeats",
                "3",
            ],
        )

        call_count = 0

        def fake_run_prompt(config, prompt):
            nonlocal call_count
            call_count += 1
            # Tasks repeat in order: t-ok x3, t-bad x3
            # call_count 4 = 2nd task, 2nd repeat
            if call_count == 5:
                raise RuntimeError("model exploded")
            return _make_model_result(response="answer", latency_sec=0.25)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch("run_benchmark.write_raw_results") as mock_write:
                    main()
                    written_results = mock_write.call_args[0][0]
                    assert len(written_results) == 6
                    passed_count = sum(1 for r in written_results if r["passed"])
                    failed_count = sum(1 for r in written_results if not r["passed"])
                    assert passed_count == 5
                    assert failed_count == 1
                    # Find the failed result
                    failed_result = next(r for r in written_results if not r["passed"])
                    assert failed_result["repeat_index"] == 1
                    assert failed_result["repeat_count"] == 3
                    assert "model exploded" == failed_result["reason"]

        captured = capsys.readouterr()
        out = captured.out
        assert "Total tasks: 2 (repeats=3, total_attempts=6)" in out
        assert "Passed: 5" in out


# ---------------------------------------------------------------------------
# Phase 1 backward-compatibility contract tests
# ---------------------------------------------------------------------------


class TestDryRunContract:
    """Contract tests proving --dry-run still works with a sample task file."""

    def test_dry_run_contract(self, monkeypatch, tmp_path, capsys):
        """--dry-run prints inspection info and does NOT call run_prompt."""
        config_path = tmp_path / "config.yaml"
        task_path = tmp_path / "tasks.jsonl"
        _write_yaml(config_path, _make_config(config_id="contract-cfg"))
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "What is 2+2?", "math", "4"),
                _make_task("t-02", "Say hello", "text", "hello"),
            ],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_benchmark.py",
                "--config",
                str(config_path),
                "--task-file",
                str(task_path),
                "--dry-run",
            ],
        )

        with patch("runners.benchmark_runner.run_prompt") as mock_prompt:
            main()
            mock_prompt.assert_not_called()

        captured = capsys.readouterr()
        out = captured.out
        assert "Config: contract-cfg" in out
        assert "Tasks: 2" in out
        assert 't-01: "What is 2+2?" -> numeric_close' in out
        assert 't-02: "Say hello" -> exact_match' in out


class TestSummaryCsvColumnsContract:
    """Contract tests proving summary CSV preserves Phase 1 fields plus Task 16 fields."""

    EXPECTED_COLUMNS = [
        "run_id",
        "model_config_id",
        "task_file",
        "total_tasks",
        "total_attempts",
        "passed",
        "failed",
        "pass_rate",
        "average_score",
        "average_latency_sec",
        "repeats",
        "suite_id",
        "suite_name",
        "run_folder",
        "status",
        "started_at",
        "completed_at",
        "artifact_count",
    ]

    def test_summary_csv_header_contract(self, monkeypatch, tmp_path):
        """append_summary produces the expanded Task 16 CSV schema."""
        monkeypatch.chdir(tmp_path)
        results = [
            {
                "latency_sec": 0.5,
                "score": 1.0,
                "passed": True,
                "repeat_index": 0,
                "repeat_count": 1,
            },
        ]
        append_summary(results, "cfg", "tasks.jsonl", "run-1", repeats=1, total_tasks=1)
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        header = lines[0].split(",")
        assert header == self.EXPECTED_COLUMNS

    def test_summary_csv_can_be_read_by_generate_leaderboard(
        self, monkeypatch, tmp_path
    ):
        """A CSV produced by append_summary can be consumed by generate_leaderboard."""
        monkeypatch.chdir(tmp_path)
        results = [
            {
                "latency_sec": 1.234,
                "score": 0.85,
                "passed": True,
                "repeat_index": 0,
                "repeat_count": 1,
            },
            {
                "latency_sec": 2.345,
                "score": 0.65,
                "passed": False,
                "repeat_index": 0,
                "repeat_count": 1,
            },
        ]
        append_summary(results, "cfg", "tasks.jsonl", "run-1", repeats=1, total_tasks=2)
        summary_path = tmp_path / "results" / "summary.csv"
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        generate_leaderboard(str(summary_path), str(output_path))

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "cfg" in content
        assert "tasks.jsonl" in content
        # Basic sanity that values are present in the leaderboard
        assert "0.75" in content  # average_score
        assert "50.0%" in content  # pass rate (1 passed / 2 total)


class TestResumeCli:
    """Batch CLI resume behavior."""

    def _make_resume_run(
        self,
        tmp_path,
        status: str = "cancelled",
        repeats: int = 1,
        raw_rows: list[dict] | None = None,
    ):
        task_path = tmp_path / "tasks.jsonl"
        _write_jsonl(
            task_path,
            [
                _make_task("t-01", "Q1", "text", "a1"),
                _make_task("t-02", "Q2", "text", "a2"),
            ],
        )
        run_dir = tmp_path / "results" / "runs" / "resume-cfg" / "run-1"
        run_dir.mkdir(parents=True)
        manifest = {
            "run_id": "run-1",
            "model_config_id": "resume-cfg",
            "model_name": "Resume Model",
            "task_file": str(task_path),
            "server_url": "http://127.0.0.1:8080/v1/chat/completions",
            "settings": {"temperature": 0, "top_p": 1, "max_tokens": 128},
            "status": status,
            "started_at": "2026-05-03T12:00:00",
            "completed_at": None,
            "repeats": repeats,
        }
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        raw_path = run_dir / "raw.jsonl"
        if raw_rows is None:
            raw_rows = [
                {
                    "run_id": "run-1",
                    "model_config_id": "resume-cfg",
                    "task_file": str(task_path),
                    "task_id": "t-01",
                    "category": "text",
                    "prompt": "Q1",
                    "expected": "a1",
                    "response": "answer",
                    "latency_sec": 0.5,
                    "score": 1.0,
                    "passed": True,
                    "reason": "ok",
                    "settings": {},
                    "artifact_paths": [],
                    "repeat_index": 0,
                    "repeat_count": repeats,
                }
            ]
        _write_jsonl(raw_path, raw_rows)
        return run_dir

    def test_resume_continues_missing_attempts_without_repeating_completed(
        self, monkeypatch, tmp_path, capsys
    ):
        monkeypatch.chdir(tmp_path)
        run_dir = self._make_resume_run(tmp_path)
        monkeypatch.setattr(sys, "argv", ["run_benchmark.py", "--resume", str(run_dir)])

        prompts: list[str] = []

        def fake_run_prompt(config, prompt):
            prompts.append(prompt)
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                with patch("run_benchmark.generate_leaderboard") as mock_lb:
                    main()

        assert prompts == ["Q2"]
        lines = (run_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        rows = [json.loads(line) for line in lines]
        assert [(row["task_id"], row["repeat_index"]) for row in rows] == [
            ("t-01", 0),
            ("t-02", 0),
        ]
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "completed"
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        assert summary["total_attempts"] == 2
        assert summary["passed"] == 2
        assert (tmp_path / "results" / "summary.csv").exists()
        mock_lb.assert_called_once()

        out = capsys.readouterr().out
        assert "Resuming run:" in out
        assert "Completed attempts found: 1/2" in out
        assert "Missing attempts to run: 1" in out
        assert "[2/2] t-02 (repeat 1/1)" in out

    def test_resume_rejects_completed_runs(self, monkeypatch, tmp_path, capsys):
        run_dir = self._make_resume_run(tmp_path, status="completed")
        monkeypatch.setattr(sys, "argv", ["run_benchmark.py", "--resume", str(run_dir)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "already completed" in capsys.readouterr().err

    def test_resume_warns_about_corrupted_raw_lines(
        self, monkeypatch, tmp_path, capsys
    ):
        monkeypatch.chdir(tmp_path)
        run_dir = self._make_resume_run(tmp_path)
        with (run_dir / "raw.jsonl").open("a", encoding="utf-8") as fh:
            fh.write("{bad json\n")
        monkeypatch.setattr(sys, "argv", ["run_benchmark.py", "--resume", str(run_dir)])

        def fake_run_prompt(config, prompt):
            return _make_model_result(response="answer", latency_sec=0.5)

        def fake_scorer(task, response):
            return _make_score_result(score=1.0, passed=True, reason="matched")

        with patch("runners.benchmark_runner.run_prompt", side_effect=fake_run_prompt):
            with patch("runners.benchmark_runner.get_scorer", return_value=fake_scorer):
                main()

        assert "WARNING: raw.jsonl line 2" in capsys.readouterr().err

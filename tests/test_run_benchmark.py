"""Comprehensive unit and integration tests for run_benchmark.py.

Tests cover helper functions in isolation and `main()` through
monkey-patching of external dependencies and `sys.argv`.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
import yaml

from run_benchmark import (
    CATEGORY_SCORER_MAP,
    _FALLBACK_SCORER,
    _build_error_result,
    _build_result,
    _extract_settings,
    _resolve_scorer,
    main,
)
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
        assert _resolve_scorer(task) == _FALLBACK_SCORER

    def test_empty_string_category_uses_fallback(self):
        """Empty string category falls back to exact_match."""
        task = _make_task(category="")
        assert _resolve_scorer(task) == _FALLBACK_SCORER

    def test_missing_category_uses_fallback(self):
        """Missing category key inside metadata falls back."""
        task = _make_task(category="general")
        del task["metadata"]["category"]
        assert _resolve_scorer(task) == _FALLBACK_SCORER

    def test_missing_metadata_uses_fallback(self):
        """Missing metadata entirely falls back."""
        task = _make_task(category="general")
        del task["metadata"]
        assert _resolve_scorer(task) == _FALLBACK_SCORER


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
            "run_id,model_config_id,task_file,total_tasks,passed,failed,"
            "pass_rate,average_score,average_latency_sec"
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
        """All-passed results produce pass_rate=1.0 and correct averages."""
        monkeypatch.chdir(tmp_path)
        results = [
            {"latency_sec": 0.5, "score": 0.8, "passed": True},
            {"latency_sec": 1.5, "score": 1.0, "passed": True},
            {"latency_sec": 1.0, "score": 0.9, "passed": True},
        ]
        append_summary(results, "cfg", "tasks.jsonl", "run-1")
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[3] == "3"
        assert parts[4] == "3"
        assert parts[5] == "0"
        assert parts[6] == "1.0000"
        assert float(parts[7]) == pytest.approx(0.9, abs=0.0001)
        assert float(parts[8]) == pytest.approx(1.0, abs=0.001)

    def test_stats_computation_some_failed(self, monkeypatch, tmp_path, sample_results):
        """Mixed-pass results produce correct pass_rate and averages."""
        monkeypatch.chdir(tmp_path)
        append_summary(sample_results, "cfg", "tasks.jsonl", "run-1")
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[3] == "3"
        assert parts[4] == "2"
        assert parts[5] == "1"
        assert parts[6] == "0.6667"
        assert float(parts[7]) == pytest.approx(0.6667, abs=0.0001)
        assert float(parts[8]) == pytest.approx(1.000, abs=0.001)

    def test_empty_results_list(self, monkeypatch, tmp_path):
        """Empty results produce zeroes across all summary columns."""
        monkeypatch.chdir(tmp_path)
        append_summary([], "cfg", "tasks.jsonl", "run-1")
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[3] == "0"
        assert parts[4] == "0"
        assert parts[5] == "0"
        assert parts[6] == "0.0000"
        assert parts[7] == "0.0000"
        assert parts[8] == "0.000"

    def test_float_formatting(self, monkeypatch, tmp_path):
        """pass_rate uses :.4f and average_latency_sec uses :.3f."""
        monkeypatch.chdir(tmp_path)
        results = [
            {"latency_sec": 1.23456, "score": 0.666666, "passed": True},
            {"latency_sec": 1.23456, "score": 0.666666, "passed": False},
        ]
        append_summary(results, "cfg", "tasks.jsonl", "run-1")
        summary_path = tmp_path / "results" / "summary.csv"
        with open(summary_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        data = lines[1]
        parts = data.split(",")
        assert parts[6] == "0.5000"  # 1 passed / 2 total -> .4f
        assert parts[7] == "0.6667"  # avg score -> .4f
        assert parts[8] == "1.235"  # avg latency -> .3f


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

        with patch("run_benchmark.run_prompt") as mock_prompt:
            main()
            mock_prompt.assert_not_called()

        captured = capsys.readouterr()
        out = captured.out
        assert "Config: dry-run-cfg" in out
        assert "Tasks: 2" in out
        assert 't-01: "What is 2+2?" -> numeric_close' in out
        assert 't-02: "Say hello" -> exact_match' in out


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

        with patch("run_benchmark.run_prompt", side_effect=fake_run_prompt):
            with patch("run_benchmark.get_scorer", return_value=fake_scorer):
                main()

        captured = capsys.readouterr()
        out = captured.out
        assert "[1/2] t-01" in out
        assert "[2/2] t-02" in out
        assert "Total tasks: 2" in out
        assert "Passed: 2" in out
        assert "Average score: 1.00" in out
        assert "Average latency: 0.50s" in out

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

        with patch("run_benchmark.run_prompt", side_effect=fake_run_prompt):
            with patch("run_benchmark.get_scorer", return_value=fake_scorer):
                main()

        captured = capsys.readouterr()
        out = captured.out
        assert "[1/2] t-ok" in out
        assert "[2/2] t-bad" in out
        assert "Total tasks: 2" in out
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

        with patch("run_benchmark.run_prompt", side_effect=fake_run_prompt):
            with patch("run_benchmark.get_scorer", return_value=fake_scorer):
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

        with patch("run_benchmark.run_prompt", side_effect=fake_run_prompt):
            with patch("run_benchmark.get_scorer", return_value=fake_scorer):
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

        with patch("run_benchmark.run_prompt", side_effect=fake_run_prompt):
            with patch("run_benchmark.get_scorer", return_value=fake_scorer):
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

        with patch("run_benchmark.run_prompt", side_effect=fake_run_prompt):
            with patch("run_benchmark.get_scorer", return_value=fake_scorer):
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

        with patch("run_benchmark.run_prompt", side_effect=fake_run_prompt):
            with patch("run_benchmark.get_scorer", return_value=fake_scorer):
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

        with patch("run_benchmark.run_prompt", side_effect=fake_run_prompt):
            with patch("run_benchmark.get_scorer", return_value=fake_scorer):
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

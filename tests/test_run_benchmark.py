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

"""Comprehensive unit tests for runners.benchmark_runner.

Tests cover the public ``run_benchmark`` API as well as internal helper
functions extracted from the root CLI.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from runners.benchmark_runner import (
    BenchmarkCancelled,
    CATEGORY_SCORER_MAP,
    _FALLBACK_SCORER,
    _build_error_result,
    _build_result,
    _extract_settings,
    _resolve_scorer,
    run_benchmark,
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


# ---------------------------------------------------------------------------
# A. Basic execution
# ---------------------------------------------------------------------------


class TestRunBenchmarkNormal:
    """Normal execution of ``run_benchmark``."""

    def test_normal_run_two_tasks_one_repeat(self):
        """Two tasks, one repeat each — verify summary shape and per-result fields."""
        config = _make_config(config_id="cfg-01")
        tasks = [
            _make_task("t-01", "Q1", "text", "a1"),
            _make_task("t-02", "Q2", "math", "42"),
        ]
        options = {"repeats": 1, "run_id": "run-123"}

        with patch("runners.benchmark_runner.run_prompt") as mock_run_prompt:
            mock_run_prompt.return_value = _make_model_result("answer", 0.5)

            with patch("runners.benchmark_runner.get_scorer") as mock_get_scorer:
                mock_get_scorer.return_value = (
                    lambda task, response: _make_score_result(1.0, True, "ok")
                )

                result = run_benchmark(config, tasks, options)

        # Summary assertions
        assert isinstance(result, dict)
        assert result["run_id"] == "run-123"
        assert result["total_tasks"] == 2
        assert result["total_attempts"] == 2
        assert result["passed"] == 2
        assert result["failed"] == 0
        assert result["average_score"] == 1.0
        assert result["average_latency_sec"] == 0.5

        # Results list assertions
        results = result["results"]
        assert len(results) == 2

        expected_fields = {
            "run_id",
            "model_config_id",
            "task_id",
            "category",
            "task_file",
            "prompt",
            "expected",
            "response",
            "latency_sec",
            "score",
            "passed",
            "reason",
            "settings",
            "repeat_index",
            "repeat_count",
            "artifact_paths",
        }

        for r in results:
            assert set(r.keys()) == expected_fields
            assert r["run_id"] == "run-123"
            assert r["model_config_id"] == "cfg-01"
            assert r["repeat_count"] == 1
            assert r["repeat_index"] == 0
            assert r["response"] == "answer"
            assert r["latency_sec"] == 0.5
            assert r["score"] == 1.0
            assert r["passed"] is True

        assert results[0]["task_id"] == "t-01"
        assert results[0]["category"] == "text"
        assert results[1]["task_id"] == "t-02"
        assert results[1]["category"] == "math"

    def test_error_handling_one_task_raises(self):
        """One task succeeds, one raises — verify error result fields and continued execution."""
        config = _make_config(config_id="cfg-err")
        tasks = [
            _make_task("t-ok", "OK task", "text", "ok"),
            _make_task("t-bad", "Bad task", "text", "bad"),
        ]
        options = {"repeats": 1, "run_id": "run-err"}

        call_count = 0

        def side_effect(config, prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("model exploded")
            return _make_model_result("answer", 0.25)

        with patch("runners.benchmark_runner.run_prompt", side_effect=side_effect):
            with patch("runners.benchmark_runner.get_scorer") as mock_get_scorer:
                mock_get_scorer.return_value = (
                    lambda task, response: _make_score_result(1.0, True, "ok")
                )

                result = run_benchmark(config, tasks, options)

        results = result["results"]
        assert len(results) == 2
        assert result["passed"] == 1
        assert result["failed"] == 1
        assert result["total_tasks"] == 2

        # Success result
        ok = results[0]
        assert ok["task_id"] == "t-ok"
        assert ok["passed"] is True
        assert ok["score"] == 1.0
        assert ok["response"] == "answer"
        assert ok["latency_sec"] == 0.25

        # Error result
        bad = results[1]
        assert bad["task_id"] == "t-bad"
        assert bad["passed"] is False
        assert bad["score"] == 0.0
        assert bad["response"] == ""
        assert bad["latency_sec"] == 0.0
        assert "model exploded" in bad["reason"]


# ---------------------------------------------------------------------------
# B. Repeats
# ---------------------------------------------------------------------------


class TestRunBenchmarkRepeats:
    """Execution with ``repeats`` > 1."""

    def test_repeats_3_two_tasks(self):
        """2 tasks x 3 repeats = 6 results with correct repeat_index values."""
        config = _make_config(config_id="cfg-rep")
        tasks = [
            _make_task("t-01", "Q1", "text", "a1"),
            _make_task("t-02", "Q2", "text", "a2"),
        ]
        options = {"repeats": 3, "run_id": "run-rep"}

        with patch("runners.benchmark_runner.run_prompt") as mock_run_prompt:
            mock_run_prompt.return_value = _make_model_result("answer", 0.5)

            with patch("runners.benchmark_runner.get_scorer") as mock_get_scorer:
                mock_get_scorer.return_value = (
                    lambda task, response: _make_score_result(1.0, True, "ok")
                )

                result = run_benchmark(config, tasks, options)

        results = result["results"]
        assert len(results) == 6
        assert result["total_attempts"] == 6
        assert result["passed"] == 6
        assert result["failed"] == 0

        repeat_indices = [r["repeat_index"] for r in results]
        repeat_counts = [r["repeat_count"] for r in results]
        assert repeat_indices == [0, 1, 2, 0, 1, 2]
        assert all(rc == 3 for rc in repeat_counts)

    def test_repeats_with_one_error(self):
        """5/6 pass, 1 fails on middle repeat of second task."""
        config = _make_config(config_id="cfg-rep-err")
        tasks = [
            _make_task("t-ok", "OK task", "text", "ok"),
            _make_task("t-bad", "Bad task", "text", "bad"),
        ]
        options = {"repeats": 3, "run_id": "run-rep-err"}

        call_count = 0

        def side_effect(config, prompt):
            nonlocal call_count
            call_count += 1
            # Order: t-ok x3, t-bad x3
            if call_count == 5:  # 2nd task, 2nd repeat
                raise RuntimeError("model exploded")
            return _make_model_result("answer", 0.25)

        with patch("runners.benchmark_runner.run_prompt", side_effect=side_effect):
            with patch("runners.benchmark_runner.get_scorer") as mock_get_scorer:
                mock_get_scorer.return_value = (
                    lambda task, response: _make_score_result(1.0, True, "ok")
                )

                result = run_benchmark(config, tasks, options)

        results = result["results"]
        assert len(results) == 6
        assert result["passed"] == 5
        assert result["failed"] == 1

        failed = next(r for r in results if not r["passed"])
        assert failed["task_id"] == "t-bad"
        assert failed["repeat_index"] == 1
        assert failed["repeat_count"] == 3
        assert "model exploded" in failed["reason"]


# ---------------------------------------------------------------------------
# C. Dry-run
# ---------------------------------------------------------------------------


class TestRunBenchmarkDryRun:
    """Dry-run mode skips model calls."""

    def test_dry_run_no_model_calls_and_zero_stats(self):
        """Dry-run must not call run_prompt and must return empty results with zero stats."""
        config = _make_config(config_id="cfg-dry")
        tasks = [
            _make_task("t-01", "Q1", "text", "a1"),
            _make_task("t-02", "Q2", "text", "a2"),
        ]
        options = {"repeats": 3, "dry_run": True, "run_id": "run-dry"}

        with patch("runners.benchmark_runner.run_prompt") as mock_run_prompt:
            result = run_benchmark(config, tasks, options)
            mock_run_prompt.assert_not_called()

        assert result["results"] == []
        assert result["run_id"] == "run-dry"
        assert result["total_tasks"] == 2
        assert result["total_attempts"] == 6
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["average_score"] == 0.0
        assert result["average_latency_sec"] == 0.0


# ---------------------------------------------------------------------------
# D. Callbacks
# ---------------------------------------------------------------------------


class TestRunBenchmarkCallbacks:
    """Progress and result callback invocation."""

    def test_progress_callback_called_with_correct_values(self):
        """For 2 tasks x 3 repeats, progress callback receives (1,6) through (6,6)."""
        config = _make_config()
        tasks = [
            _make_task("t-01", "Q1", "text", "a1"),
            _make_task("t-02", "Q2", "text", "a2"),
        ]
        options = {"repeats": 3, "run_id": "run-cb"}

        progress_calls: list[tuple[int, int]] = []

        def progress_callback(completed: int, total: int) -> None:
            progress_calls.append((completed, total))

        with patch("runners.benchmark_runner.run_prompt") as mock_run_prompt:
            mock_run_prompt.return_value = _make_model_result("answer", 0.5)

            with patch("runners.benchmark_runner.get_scorer") as mock_get_scorer:
                mock_get_scorer.return_value = (
                    lambda task, response: _make_score_result(1.0, True, "ok")
                )

                run_benchmark(
                    config, tasks, options, progress_callback=progress_callback
                )

        assert progress_calls == [(1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6)]

    def test_result_callback_called_after_each_attempt(self):
        """Result callback is invoked 6 times for 2 tasks x 3 repeats."""
        config = _make_config()
        tasks = [
            _make_task("t-01", "Q1", "text", "a1"),
            _make_task("t-02", "Q2", "text", "a2"),
        ]
        options = {"repeats": 3, "run_id": "run-cb"}

        result_calls: list[dict] = []

        def result_callback(result: dict) -> None:
            result_calls.append(result)

        with patch("runners.benchmark_runner.run_prompt") as mock_run_prompt:
            mock_run_prompt.return_value = _make_model_result("answer", 0.5)

            with patch("runners.benchmark_runner.get_scorer") as mock_get_scorer:
                mock_get_scorer.return_value = (
                    lambda task, response: _make_score_result(1.0, True, "ok")
                )

                run_benchmark(config, tasks, options, result_callback=result_callback)

        assert len(result_calls) == 6
        assert result_calls[0]["task_id"] == "t-01"
        assert result_calls[0]["repeat_index"] == 0
        assert result_calls[5]["task_id"] == "t-02"
        assert result_calls[5]["repeat_index"] == 2

    def test_no_callbacks_runs_without_error(self):
        """Both callbacks None must not raise and still produce correct result."""
        config = _make_config()
        tasks = [_make_task("t-01", "Q1", "text", "a1")]
        options = {"repeats": 1, "run_id": "run-none"}

        with patch("runners.benchmark_runner.run_prompt") as mock_run_prompt:
            mock_run_prompt.return_value = _make_model_result("answer", 0.5)

            with patch("runners.benchmark_runner.get_scorer") as mock_get_scorer:
                mock_get_scorer.return_value = (
                    lambda task, response: _make_score_result(1.0, True, "ok")
                )

                result = run_benchmark(config, tasks, options)

        assert result["passed"] == 1
        assert result["failed"] == 0
        assert len(result["results"]) == 1

    def test_cancel_callback_stops_before_next_attempt(self):
        config = _make_config()
        tasks = [
            _make_task("t-01", "Q1", "text", "a1"),
            _make_task("t-02", "Q2", "text", "a2"),
        ]
        options = {"repeats": 1, "run_id": "run-cancel"}
        completed: list[dict] = []

        def cancel_callback() -> bool:
            return len(completed) == 1

        with patch("runners.benchmark_runner.run_prompt") as mock_run_prompt:
            mock_run_prompt.return_value = _make_model_result("answer", 0.5)
            with patch("runners.benchmark_runner.get_scorer") as mock_get_scorer:
                mock_get_scorer.return_value = (
                    lambda task, response: _make_score_result(1.0, True, "ok")
                )

                with pytest.raises(BenchmarkCancelled):
                    run_benchmark(
                        config,
                        tasks,
                        options,
                        result_callback=completed.append,
                        cancel_callback=cancel_callback,
                    )

        assert [result["task_id"] for result in completed] == ["t-01"]
        assert mock_run_prompt.call_count == 1


# ---------------------------------------------------------------------------
# E. Runner-specific helpers
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

    def test_missing_category_key_uses_fallback(self):
        """Missing category key inside metadata falls back."""
        task = _make_task(category="general")
        del task["metadata"]["category"]
        assert _resolve_scorer(task) == _FALLBACK_SCORER

    def test_missing_metadata_uses_fallback(self):
        """Missing metadata entirely falls back."""
        task = _make_task(category="general")
        del task["metadata"]
        assert _resolve_scorer(task) == _FALLBACK_SCORER


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
# F. Import verification
# ---------------------------------------------------------------------------


class TestRunnerImports:
    """Verify that benchmark_runner can import its dependencies correctly."""

    def test_run_prompt_is_importable_via_benchmark_runner(self):
        """The runner module must be able to resolve run_prompt locally."""
        import runners.benchmark_runner as br

        assert callable(br.run_prompt)

    def test_get_scorer_is_importable_via_benchmark_runner(self):
        """The runner module must be able to resolve get_scorer locally."""
        import runners.benchmark_runner as br

        assert callable(br.get_scorer)

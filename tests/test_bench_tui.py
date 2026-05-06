from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _make_task(task_id: str = "t-01") -> dict:
    return {
        "id": task_id,
        "description": "Say ok",
        "command": "noop",
        "expected_output": "ok",
        "metadata": {"category": "text"},
    }


def _make_config(config_id: str = "cfg-1") -> dict:
    return {
        "id": config_id,
        "model_name": "Config One",
        "runtime": {"server_url": "http://127.0.0.1:8080/v1/chat/completions"},
        "settings": {"temperature": 0, "top_p": 1, "max_tokens": 128},
    }


def _make_suite(task_file: Path) -> dict:
    return {
        "id": "reasoning.math",
        "name": "Math",
        "category": "reasoning",
        "task_file": str(task_file),
        "description": "Math suite",
        "scoring": "deterministic",
    }


def test_smoke_test_cli_exits_successfully():
    result = subprocess.run(
        [sys.executable, "bench_tui.py", "--smoke-test"],
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "TUI smoke test passed" in result.stdout


def test_app_initializes_core_screens_under_textual_test_harness():
    from bench_tui import (
        BenchmarkTuiApp,
        DashboardScreen,
        ModelSelectionScreen,
        ResultsBrowserScreen,
        RunProgressScreen,
        RunSettingsScreen,
        SuiteSelectionScreen,
    )

    async def run_app() -> None:
        app = BenchmarkTuiApp(smoke_test=True)
        async with app.run_test():
            assert isinstance(app.screen, DashboardScreen)
            app.push_screen(ModelSelectionScreen())
            assert isinstance(app.screen, ModelSelectionScreen)
            app.pop_screen()
            app.push_screen(SuiteSelectionScreen())
            assert isinstance(app.screen, SuiteSelectionScreen)
            app.pop_screen()
            app.push_screen(RunSettingsScreen())
            assert isinstance(app.screen, RunSettingsScreen)
            app.pop_screen()
            app.push_screen(RunProgressScreen())
            assert isinstance(app.screen, RunProgressScreen)
            app.pop_screen()
            app.push_screen(ResultsBrowserScreen())
            assert isinstance(app.screen, ResultsBrowserScreen)

    asyncio.run(run_app())


def test_registry_load_errors_are_captured_as_app_state(monkeypatch):
    from bench_tui import BenchmarkTuiApp

    monkeypatch.setattr(
        "bench_tui.list_model_configs",
        lambda: (_ for _ in ()).throw(ValueError("bad models")),
    )
    monkeypatch.setattr("bench_tui.list_suites", lambda: [])

    app = BenchmarkTuiApp(smoke_test=True)
    app.load_registries()

    assert app.model_configs == []
    assert any("bad models" in error for error in app.registry_errors)


@pytest.mark.parametrize(
    ("repeats", "max_tasks", "expected"),
    [
        ("1", "", (1, None)),
        ("3", "10", (3, 10)),
        (" 2 ", " 5 ", (2, 5)),
    ],
)
def test_validate_run_settings_accepts_positive_values(repeats, max_tasks, expected):
    from bench_tui import validate_run_settings

    assert validate_run_settings(repeats, max_tasks) == expected


@pytest.mark.parametrize(
    ("repeats", "max_tasks"),
    [
        ("0", ""),
        ("-1", ""),
        ("abc", ""),
        ("1", "0"),
        ("1", "-2"),
        ("1", "abc"),
    ],
)
def test_validate_run_settings_rejects_invalid_values(repeats, max_tasks):
    from bench_tui import validate_run_settings

    with pytest.raises(ValueError):
        validate_run_settings(repeats, max_tasks)


def test_execute_suite_run_marks_cancelled_and_writes_partial_summary(tmp_path, monkeypatch):
    from bench_tui import RunSettings, execute_suite_run
    from runners.benchmark_runner import BenchmarkCancelled

    monkeypatch.chdir(tmp_path)
    task_file = tmp_path / "benchmarks" / "reasoning" / "math.jsonl"
    _write_jsonl(task_file, [_make_task("t-01"), _make_task("t-02")])

    completed_result = {
        "run_id": "run-1",
        "model_config_id": "cfg-1",
        "task_file": str(task_file),
        "task_id": "t-01",
        "category": "text",
        "prompt": "Say ok",
        "expected": "ok",
        "response": "ok",
        "latency_sec": 0.25,
        "score": 1.0,
        "passed": True,
        "reason": "matched",
        "settings": {},
        "artifact_paths": [],
        "repeat_index": 0,
        "repeat_count": 1,
    }

    def fake_run_benchmark(*args, result_callback=None, cancel_callback=None, **kwargs):
        assert cancel_callback is not None
        assert cancel_callback() is True
        result_callback(completed_result)
        raise BenchmarkCancelled("cancelled")

    monkeypatch.setattr("bench_tui.run_benchmark", fake_run_benchmark)

    outcome = execute_suite_run(
        _make_config(),
        _make_suite(task_file),
        RunSettings(repeats=1),
        cancel_callback=lambda: True,
    )

    assert outcome.status == "cancelled"
    manifest = json.loads((outcome.run_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((outcome.run_dir / "summary.json").read_text(encoding="utf-8"))
    raw_lines = (outcome.run_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()

    assert manifest["status"] == "cancelled"
    assert summary["status"] == "cancelled"
    assert summary["passed"] == 1
    assert len(raw_lines) == 1


def test_discover_result_runs_reads_manifests_and_marks_resumable(tmp_path):
    from bench_tui import discover_result_runs

    run_dir = tmp_path / "results" / "runs" / "cfg-1" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "model_config_id": "cfg-1",
                "suite_id": "reasoning.math",
                "suite_name": "Math",
                "task_file": "benchmarks/reasoning/math.jsonl",
                "status": "cancelled",
                "started_at": "2026-05-05T12:00:00",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "summary.json").write_text(
        json.dumps({"average_score": 0.75, "pass_rate": 0.5}),
        encoding="utf-8",
    )

    runs = discover_result_runs(tmp_path / "results" / "runs")

    assert len(runs) == 1
    assert runs[0].run_id == "run-1"
    assert runs[0].suite_label == "reasoning.math"
    assert runs[0].is_resumable is True
    assert runs[0].summary["average_score"] == 0.75

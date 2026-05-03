#!/usr/bin/env python3
"""Generate run_benchmark.py and test_suite_registry.py with correct content."""

import base64
import os

PROJECT = r"F:\Personal\LocalModelTesting\7800XT-LocalModelBenchMark"


def b64(content: str) -> str:
    return base64.b64encode(content.encode("utf-8")).decode("ascii")


def write_b64(target: str, b64_content: str):
    path = os.path.join(PROJECT, target)
    data = base64.b64decode(b64_content).decode("utf-8")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
    print(f"Written {target}: {len(data)} chars")


# =====================================================================
# run_benchmark.py
# =====================================================================

RUN_BENCHMARK_B64 = b64(r'''"""Local Model Benchmark Harness - orchestrates config loading, model prompting,
and scoring across a JSONL task file to produce per-task results and a summary.
Supports direct task files (--task-file) or named benchmark suites (--suite).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
import uuid
from typing import Any

from runners.config_loader import load_config
from runners.llama_client import run_prompt
from runners.leaderboard import generate_leaderboard
from runners.result_writer import append_summary, write_raw_results
from runners.task_loader import load_tasks
from runners.suite_registry import get_suite
from scorers.registry import get_scorer


CATEGORY_SCORER_MAP: dict[str, str] = {
    "math": "numeric_close",
    "numeric": "numeric_close",
    "text": "exact_match",
    "general": "exact_match",
    "keyword": "keyword_match",
    "code": "keyword_match",
    "json": "json_valid",
    "tool": "json_valid",
}

_FALLBACK_SCORER = "exact_match"


def _resolve_scorer(task: dict[str, Any]) -> str:
    category: str = task.get("metadata", {}).get("category", "")
    return CATEGORY_SCORER_MAP.get(category, _FALLBACK_SCORER)


def _extract_settings(config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("settings", {})
    return {
        "context_size": settings.get("context_size"),
        "temperature": settings.get("temperature"),
        "top_p": settings.get("top_p"),
        "max_tokens": settings.get("max_tokens"),
    }


def _build_result(
    task: dict[str, Any],
    config: dict[str, Any],
    model_result: dict[str, Any],
    score_result: dict[str, Any],
    task_file: str,
    run_id: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "model_config_id": config["id"],
        "task_id": task["id"],
        "category": task.get("metadata", {}).get("category", ""),
        "task_file": task_file,
        "prompt": task["description"],
        "expected": task.get("expected_output", ""),
        "response": model_result["response"],
        "latency_sec": model_result["latency_sec"],
        "score": score_result["score"],
        "passed": score_result["passed"],
        "reason": score_result["reason"],
        "settings": _extract_settings(config),
    }


def _build_error_result(
    task: dict[str, Any],
    config: dict[str, Any],
    error: str,
    task_file: str,
    run_id: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "model_config_id": config["id"],
        "task_id": task["id"],
        "category": task.get("metadata", {}).get("category", ""),
        "task_file": task_file,
        "prompt": task["description"],
        "expected": task.get("expected_output", ""),
        "response": "",
        "latency_sec": 0.0,
        "score": 0.0,
        "passed": False,
        "reason": str(error),
        "settings": _extract_settings(config),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Model Benchmark Harness")
    parser.add_argument("--config", required=True, help="Path to YAML config file")

    task_source = parser.add_mutually_exclusive_group(required=True)
    task_source.add_argument(
        "--task-file",
        help="Path to JSONL task file (mutually exclusive with --suite)",
    )
    task_source.add_argument(
        "--suite",
        help="Benchmark suite ID from benchmarks/suites.yaml"
             " (mutually exclusive with --task-file)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load config and tasks, print what would run, but do NOT call the model",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Number of times to repeat each task (default: 1)",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading config: {exc}", file=sys.stderr)
        sys.exit(1)

    task_file: str
    suite_info: dict[str, Any] | None = None
    if args.suite:
        try:
            suite_info = get_suite(args.suite)
            task_file = suite_info["task_file"]
        except (FileNotFoundError, ValueError, KeyError) as exc:
            print(f"Error resolving suite '{args.suite}': {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        task_file = args.task_file

    try:
        tasks = load_tasks(task_file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading tasks: {exc}", file=sys.stderr)
        sys.exit(1)

    if not tasks:
        print("No tasks found in task file.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"Config: {config['id']}")
        print(f"Tasks: {len(tasks)}")
        if suite_info:
            print(f"Suite: {suite_info['id']} ({suite_info['name']})")
        if args.repeats > 1:
            print(
                f"Repeats: {args.repeats} (total attempts: {len(tasks) * args.repeats})"
            )
        for task in tasks:
            scorer_name = _resolve_scorer(task)
            description = task["description"]
            print(f'  {task["id"]}: "{description}" -> {scorer_name}')
        return

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{uuid.uuid4().hex[:8]}"
    flat_results: list[dict[str, Any]] = []

    for task in tasks:
        scorer_name = _resolve_scorer(task)
        for repeat_idx in range(args.repeats):
            prompt: str = task["description"]
            try:
                model_result = run_prompt(config, prompt)
                scorer = get_scorer(scorer_name)
                score_result = scorer(task, model_result["response"])
                result = _build_result(
                    task, config, model_result, score_result, task_file, run_id
                )
            except Exception as exc:
                result = _build_error_result(
                    task, config, str(exc), task_file, run_id
                )
            result["repeat_index"] = repeat_idx
            result["repeat_count"] = args.repeats
            flat_results.append(result)
            print(
                f"[{len(flat_results)}/{len(tasks) * args.repeats}] {task['id']}"
                f" (repeat {repeat_idx + 1}/{args.repeats})  "
                f"score={result['score']}  "
                f"latency={result['latency_sec']:.2f}s"
            )

    total = len(flat_results)
    actual_tasks = len(tasks)
    passed = sum(1 for r in flat_results if r["passed"])
    avg_score = sum(r["score"] for r in flat_results) / total if total else 0.0
    avg_latency = sum(r["latency_sec"] for r in flat_results) / total if total else 0.0

    print()
    print(
        f"Total tasks: {actual_tasks} (repeats={args.repeats}, total_attempts={total})"
    )
    print(f"Passed: {passed}")
    print(f"Average score: {avg_score:.2f}")
    print(f"Average latency: {avg_latency:.2f}s")

    try:
        raw_path = write_raw_results(flat_results, config["id"], task_file, run_id)
        print(f"Saved raw results to {raw_path}")
    except OSError as exc:
        print(f"Error writing raw results: {exc}", file=sys.stderr)

    try:
        summary_path = append_summary(
            flat_results,
            config["id"],
            task_file,
            run_id,
            repeats=args.repeats,
            total_tasks=actual_tasks,
        )
        print(f"Update summary at {summary_path}")
    except OSError as exc:
        print(f"Error writing summary: {exc}", file=sys.stderr)

    try:
        leaderboard_path = generate_leaderboard()
        print(f"Updated leaderboard at {leaderboard_path}")
    except OSError as exc:
        print(f"Error writing leaderboard: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
''')

# =====================================================================
# test_suite_registry.py
# =====================================================================

TEST_SUITE_B64 = b64(r'''# -*- coding: utf-8 -*-
"""Tests for the benchmark suite registry."""

from __future__ import annotations

import json
import os.path
import re

import pytest
import yaml

from runners.suite_registry import (
    list_suites,
    get_suite,
    clear_cache,
    _REQUIRED_SUITE_FIELDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_suites_data():
    """Return the 8 standard suites as a list of dicts."""
    return [
        {
            "id": "reasoning.math",
            "name": "Math",
            "category": "reasoning",
            "task_file": "benchmarks/reasoning/math.jsonl",
            "description": "Numeric and short-answer math prompts.",
            "scoring": "deterministic",
        },
        {
            "id": "reasoning.real_world",
            "name": "Real-World Reasoning",
            "category": "reasoning",
            "task_file": "benchmarks/reasoning/real_world.jsonl",
            "description": "Multi-step real-world reasoning tasks.",
            "scoring": "deterministic",
        },
        {
            "id": "reasoning.instruction_following",
            "name": "Instruction Following",
            "category": "reasoning",
            "task_file": "benchmarks/reasoning/instruction_following.jsonl",
            "description": "Tasks that test adherence to specific formatting.",
            "scoring": "deterministic",
        },
        {
            "id": "coding.frontend",
            "name": "Frontend Coding",
            "category": "coding",
            "task_file": "benchmarks/coding/frontend.jsonl",
            "description": "Frontend code generation.",
            "scoring": "deterministic + artifact",
        },
        {
            "id": "coding.backend",
            "name": "Backend Coding",
            "category": "coding",
            "task_file": "benchmarks/coding/backend.jsonl",
            "description": "Backend code generation.",
            "scoring": "deterministic + artifact",
        },
        {
            "id": "coding.misc",
            "name": "Misc Coding",
            "category": "coding",
            "task_file": "benchmarks/coding/misc.jsonl",
            "description": "General scripting and algorithmic coding tasks.",
            "scoring": "deterministic + artifact",
        },
        {
            "id": "tools.json_tool_calling",
            "name": "JSON Tool Calling",
            "category": "tools",
            "task_file": "benchmarks/tools/json_tool_calling.jsonl",
            "description": "Strict JSON tool-call generation.",
            "scoring": "deterministic",
        },
        {
            "id": "context.long_context",
            "name": "Long Context",
            "category": "context",
            "task_file": "benchmarks/context/long_context.jsonl",
            "description": "Long-context recall and retrieval tasks.",
            "scoring": "deterministic",
        },
    ]


@pytest.fixture
def setup_suite_env(tmp_path, valid_suites_data):
    """Set up a temporary project root with suites.yaml and stub task files."""
    for suite in valid_suites_data:
        task_rel = suite["task_file"]
        task_path = tmp_path / task_rel
        task_path.parent.mkdir(parents=True, exist_ok=True)
        task_path.write_text("", encoding="utf-8")

    suites_yaml = tmp_path / "benchmarks" / "suites.yaml"
    suites_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(str(suites_yaml), "w", encoding="utf-8") as f:
        yaml.dump({"suites": valid_suites_data}, f)

    return tmp_path


# ---------------------------------------------------------------------------
# Tests: list_suites
# ---------------------------------------------------------------------------


class TestListSuites:
    """Tests for list_suites()."""

    def test_lists_all_suites(self, setup_suite_env, valid_suites_data):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()
            suites = list_suites()
            assert len(suites) == 8
            ids = [s["id"] for s in suites]
            for suite in valid_suites_data:
                assert suite["id"] in ids
        finally:
            os.chdir(cwd)

    def test_each_suite_has_required_fields(self, setup_suite_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()
            suites = list_suites()
            for suite in suites:
                for field in _REQUIRED_SUITE_FIELDS:
                    assert field in suite, (
                        f"Suite {suite.get('id', '?')} missing {field}"
                    )
        finally:
            os.chdir(cwd)

    def test_suite_ids_follow_naming_convention(self, setup_suite_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()
            suites = list_suites()
            pattern = re.compile(r"^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*$")
            for suite in suites:
                assert pattern.match(suite["id"]), (
                    f"Suite ID {suite['id']!r} does not match "
                    f"<category>.<name> pattern"
                )
        finally:
            os.chdir(cwd)

    def test_cached_list_returns_same_data(self, setup_suite_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()
            suites1 = list_suites()
            suites2 = list_suites()
            assert suites1 == suites2
            # Modifying one should not affect the other (defensive copy)
            suites1[0]["name"] = "Changed"
            assert suites2[0]["name"] != "Changed"
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# Tests: get_suite
# ---------------------------------------------------------------------------


class TestGetSuite:
    """Tests for get_suite()."""

    def test_get_existing_suite(self, setup_suite_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()
            suite = get_suite("reasoning.math")
            assert suite["id"] == "reasoning.math"
            assert suite["name"] == "Math"
            assert suite["category"] == "reasoning"
            assert "task_file" in suite
            assert "scoring" in suite
        finally:
            os.chdir(cwd)

    def test_get_nonexistent_suite(self, setup_suite_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()
            with pytest.raises(KeyError, match="not found"):
                get_suite("nonexistent.suite")
        finally:
            os.chdir(cwd)

    def test_get_suite_returns_copy(self, setup_suite_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()
            suite = get_suite("reasoning.math")
            suite["name"] = "Modified"
            suite2 = get_suite("reasoning.math")
            assert suite2["name"] == "Math"
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# Tests: validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    """Tests for error handling in suite registry."""

    def test_missing_suites_yaml(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            clear_cache()
            with pytest.raises(FileNotFoundError, match="Suite registry not found"):
                list_suites()
        finally:
            os.chdir(cwd)

    def test_missing_task_file(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            bench_dir = tmp_path / "benchmarks"
            bench_dir.mkdir()
            suites_yaml = bench_dir / "suites.yaml"
            suites_data = {
                "suites": [
                    {
                        "id": "test.suite",
                        "name": "Test",
                        "category": "reasoning",
                        "task_file": "benchmarks/missing/file.jsonl",
                        "description": "A test suite with missing file.",
                        "scoring": "deterministic",
                    }
                ]
            }
            with open(str(suites_yaml), "w", encoding="utf-8") as f:
                yaml.dump(suites_data, f)
            clear_cache()
            with pytest.raises(ValueError, match="task_file not found"):
                list_suites()
        finally:
            os.chdir(cwd)

    def test_invalid_yaml_no_suites_key(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            bench_dir = tmp_path / "benchmarks"
            bench_dir.mkdir()
            suites_yaml = bench_dir / "suites.yaml"
            with open(str(suites_yaml), "w", encoding="utf-8") as f:
                yaml.dump({"not_suites": []}, f)
            clear_cache()
            with pytest.raises(ValueError, match="top-level.*suites"):
                list_suites()
        finally:
            os.chdir(cwd)

    def test_yaml_not_a_dict(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            bench_dir = tmp_path / "benchmarks"
            bench_dir.mkdir()
            suites_yaml = bench_dir / "suites.yaml"
            suites_yaml.write_text("just a string\n", encoding="utf-8")
            clear_cache()
            with pytest.raises(ValueError, match="top-level.*suites"):
                list_suites()
        finally:
            os.chdir(cwd)

    def test_suites_not_a_list(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            bench_dir = tmp_path / "benchmarks"
            bench_dir.mkdir()
            suites_yaml = bench_dir / "suites.yaml"
            with open(str(suites_yaml), "w", encoding="utf-8") as f:
                yaml.dump({"suites": "not_a_list"}, f)
            clear_cache()
            with pytest.raises(ValueError, match="must be a list"):
                list_suites()
        finally:
            os.chdir(cwd)

    def test_duplicate_suite_id(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            bench_dir = tmp_path / "benchmarks"
            task_dir = bench_dir / "reasoning"
            task_dir.mkdir(parents=True)
            task_file = task_dir / "math.jsonl"
            task_file.write_text("", encoding="utf-8")
            suites_yaml = bench_dir / "suites.yaml"
            suites_data = {
                "suites": [
                    {
                        "id": "reasoning.math",
                        "name": "Math 1",
                        "category": "reasoning",
                        "task_file": "benchmarks/reasoning/math.jsonl",
                        "description": "First.",
                        "scoring": "deterministic",
                    },
                    {
                        "id": "reasoning.math",
                        "name": "Math 2",
                        "category": "reasoning",
                        "task_file": "benchmarks/reasoning/math.jsonl",
                        "description": "Duplicate.",
                        "scoring": "deterministic",
                    },
                ]
            }
            with open(str(suites_yaml), "w", encoding="utf-8") as f:
                yaml.dump(suites_data, f)
            clear_cache()
            with pytest.raises(ValueError, match="Duplicate suite id"):
                list_suites()
        finally:
            os.chdir(cwd)

    def test_missing_required_fields(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            bench_dir = tmp_path / "benchmarks"
            task_dir = bench_dir / "reasoning"
            task_dir.mkdir(parents=True)
            task_file = task_dir / "math.jsonl"
            task_file.write_text("", encoding="utf-8")
            suites_yaml = bench_dir / "suites.yaml"
            suites_data = {
                "suites": [
                    {
                        "id": "reasoning.math",
                        "name": "Math",
                        "category": "reasoning",
                        "task_file": "benchmarks/reasoning/math.jsonl",
                    }
                ]
            }
            with open(str(suites_yaml), "w", encoding="utf-8") as f:
                yaml.dump(suites_data, f)
            clear_cache()
            with pytest.raises(ValueError, match="missing required fields"):
                list_suites()
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# Tests: integration with run_benchmark.py --suite arg
# ---------------------------------------------------------------------------


class TestRunBenchmarkIntegration:
    """Integration tests for --suite flag in run_benchmark.py."""

    def test_suite_dry_run(self, setup_suite_env, monkeypatch):
        """--suite with --dry-run prints suite info and resolves tasks."""
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()

            config_dir = setup_suite_env / "configs" / "models"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "test-model.yaml"
            with open(str(config_path), "w", encoding="utf-8") as f:
                yaml.dump({
                    "id": "test-model",
                    "model_name": "Test Model",
                    "runtime": {"server_url": "http://localhost:8080/v1/chat/completions"},
                    "settings": {"temperature": 0, "top_p": 1, "max_tokens": 1024},
                }, f)

            import json as _json
            task_path = setup_suite_env / "benchmarks" / "reasoning" / "math.jsonl"
            task = _json.dumps({
                "id": "math_add",
                "description": "What is 2 + 2?",
                "expected_output": "4",
                "metadata": {"category": "math"},
            })
            task_path.write_text(task + "\n", encoding="utf-8")

            from run_benchmark import main
            monkeypatch.setattr(
                "sys.argv",
                [
                    "run_benchmark.py",
                    f"--config={config_path}",
                    "--suite=reasoning.math",
                    "--dry-run",
                ],
            )
            main()
        finally:
            os.chdir(cwd)

    def test_mutually_exclusive(self, setup_suite_env, monkeypatch):
        """Using both --suite and --task-file should fail."""
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_suite_env))
            clear_cache()

            config_path = setup_suite_env / "configs" / "test-model.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(config_path), "w", encoding="utf-8") as f:
                yaml.dump({
                    "id": "test-model",
                    "model_name": "Test",
                    "runtime": {"server_url": "http://localhost:8080/v1"},
                    "settings": {"temperature": 0, "top_p": 1, "max_tokens": 1024},
                }, f)

            monkeypatch.setattr(
                "sys.argv",
                [
                    "run_benchmark.py",
                    f"--config={config_path}",
                    "--suite=reasoning.math",
                    "--task-file=benchmarks/reasoning/math.jsonl",
                ],
            )
            with pytest.raises(SystemExit):
                from run_benchmark import main
                main()
        finally:
            os.chdir(cwd)
''')


# =====================================================================
# Write all files
# =====================================================================

if __name__ == "__main__":
    # Write run_benchmark.py
    write_b64("run_benchmark.py", RUN_BENCHMARK_B64)

    # Write test_suite_registry.py
    write_b64("tests/test_suite_registry.py", TEST_SUITE_B64)

    print("All files regenerated successfully!")

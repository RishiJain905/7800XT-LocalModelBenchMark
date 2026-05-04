# -*- coding: utf-8 -*-
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
from runners.task_loader import load_tasks


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
            pattern = re.compile(r"^[a-z][a-z0-9_-]*\.[a-z][a-z0-9_-]*$")
            for suite in suites:
                assert pattern.match(suite["id"]), (
                    f"Suite ID {suite['id']!r} does not match <category>.<name> pattern"
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
            # Mutating the list should not affect the other (deep copy)
            suites1.append({"id": "extra.suite"})
            assert len(suites1) == len(suites2) + 1
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
                yaml.dump(
                    {
                        "id": "test-model",
                        "model_name": "Test Model",
                        "runtime": {
                            "server_url": "http://localhost:8080/v1/chat/completions"
                        },
                        "settings": {"temperature": 0, "top_p": 1, "max_tokens": 1024},
                    },
                    f,
                )

            import json as _json

            task_path = setup_suite_env / "benchmarks" / "reasoning" / "math.jsonl"
            task = _json.dumps(
                {
                    "id": "math_add",
                    "description": "What is 2 + 2?",
                    "expected_output": "4",
                    "metadata": {"category": "math"},
                }
            )
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
                yaml.dump(
                    {
                        "id": "test-model",
                        "model_name": "Test",
                        "runtime": {"server_url": "http://localhost:8080/v1"},
                        "settings": {"temperature": 0, "top_p": 1, "max_tokens": 1024},
                    },
                    f,
                )

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


class TestTask11ReasoningSuites:
    """Acceptance coverage for Task 11 core reasoning benchmark files."""

    REQUIRED_REASONING_SUITES = {
        "reasoning.math",
        "reasoning.real_world",
        "reasoning.instruction_following",
    }

    def test_task11_reasoning_suites_load_with_twenty_tasks(self):
        clear_cache()
        suites = {
            suite["id"]: suite
            for suite in list_suites()
            if suite["id"] in self.REQUIRED_REASONING_SUITES
        }

        assert set(suites) == self.REQUIRED_REASONING_SUITES

        for suite_id, suite in suites.items():
            tasks = load_tasks(suite["task_file"])
            assert len(tasks) == 20, f"{suite_id} should contain 20 tasks"


class TestTask12CodingSuites:
    """Acceptance coverage for Task 12 coding benchmark files."""

    REQUIRED_CODING_SUITES = {
        "coding.frontend",
        "coding.backend",
        "coding.misc",
    }

    def test_task12_coding_suites_load_with_ten_tasks_and_artifact_metadata(self):
        clear_cache()
        suites = {
            suite["id"]: suite
            for suite in list_suites()
            if suite["id"] in self.REQUIRED_CODING_SUITES
        }

        assert set(suites) == self.REQUIRED_CODING_SUITES

        for suite_id, suite in suites.items():
            tasks = load_tasks(suite["task_file"])
            assert len(tasks) == 10, f"{suite_id} should contain 10 tasks"

            for task in tasks:
                metadata = task.get("metadata", {})
                assert metadata.get("category") == "code"
                assert metadata.get("artifact_kind") in {
                    "frontend",
                    "backend",
                    "misc",
                }
                assert metadata.get("artifact_extension")
                assert metadata.get("keywords")


class TestTask13ToolCallingSuite:
    """Acceptance coverage for Task 13 JSON tool-calling benchmark file."""

    REQUIRED_TOOLS = {
        "get_weather",
        "get_forecast",
        "calculator",
        "search_files",
        "create_calendar_event",
        "draft_email",
        "extract_data",
        "book_travel",
        "generate_report",
    }

    def test_task13_tool_calling_suite_loads_with_twenty_json_tasks(self):
        clear_cache()
        suite = get_suite("tools.json_tool_calling")
        tasks = load_tasks(suite["task_file"])

        assert len(tasks) == 20

        seen_tools = set()
        for task in tasks:
            metadata = task.get("metadata", {})
            assert task.get("command") == "noop"
            assert metadata.get("category") == "json"
            assert metadata.get("expected_tool")
            assert task["expected_output"] == metadata["expected_tool"]
            assert metadata.get("required_argument_keys")
            assert isinstance(metadata["required_argument_keys"], list)
            seen_tools.add(metadata["expected_tool"])

        assert self.REQUIRED_TOOLS <= seen_tools


class TestTask14LongContextSuite:
    """Acceptance coverage for Task 14 long-context benchmark file."""

    REQUIRED_TASK_TYPES = {
        "recall",
        "buried_instruction",
        "summary_keywords",
        "cross_section_compare",
    }

    def test_task14_long_context_suite_loads_with_context_metadata(self):
        clear_cache()
        suite = get_suite("context.long_context")
        tasks = load_tasks(suite["task_file"])

        assert len(tasks) == 8

        seen_task_types = set()
        for task in tasks:
            metadata = task.get("metadata", {})
            description = task["description"]

            assert task.get("command") == "noop"
            assert len(description) >= 2500
            assert metadata.get("suite_category") == "context"
            assert metadata.get("task_type") in self.REQUIRED_TASK_TYPES
            assert isinstance(metadata.get("estimated_context_tokens"), int)
            assert metadata["estimated_context_tokens"] > 0
            assert metadata.get("prompt_size_chars") == len(description)

            seen_task_types.add(metadata["task_type"])

            if metadata["task_type"] == "summary_keywords":
                assert metadata.get("category") == "keyword"
                assert metadata.get("keywords")
                assert isinstance(metadata["keywords"], list)
                assert metadata.get("threshold") is not None
            else:
                assert metadata.get("category") == "text"

        assert seen_task_types == self.REQUIRED_TASK_TYPES

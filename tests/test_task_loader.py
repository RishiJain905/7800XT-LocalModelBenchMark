"""Tests for runners.task_loader — Task loading and validation from JSONL files."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import pytest

from runners.task_loader import load_tasks
from runners.validators import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(tmp_path, filename: str, lines: List[Dict[str, Any]]) -> str:
    """Write a list of dicts as a JSONL file and return the full path."""
    path = tmp_path / filename
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return str(path)


def _write_raw_lines(tmp_path, filename: str, lines: List[str]) -> str:
    """Write raw lines to a file and return the full path."""
    path = tmp_path / filename
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return str(path)


def _valid_task(task_id: str = "task-01") -> Dict[str, Any]:
    """Return a minimal task dict that passes all validations."""
    return {
        "id": task_id,
        "description": "A valid test task",
        "command": "echo hello",
        "expected_output": "hello",
    }


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestLoadTasksHappyPath:
    """load_tasks succeeds with well-formed JSONL files."""

    def test_single_task(self, tmp_path):
        path = _write_jsonl(tmp_path, "tasks.jsonl", [_valid_task()])
        result = load_tasks(path)
        assert len(result) == 1
        assert result[0]["id"] == "task-01"
        assert result[0]["description"] == "A valid test task"

    def test_multiple_tasks(self, tmp_path):
        tasks = [
            _valid_task("task-01"),
            _valid_task("task-02"),
            _valid_task("task-03"),
        ]
        path = _write_jsonl(tmp_path, "tasks.jsonl", tasks)
        result = load_tasks(path)
        assert len(result) == 3
        assert [t["id"] for t in result] == ["task-01", "task-02", "task-03"]

    def test_task_with_integer_id(self, tmp_path):
        task = _valid_task()
        task["id"] = 42
        path = _write_jsonl(tmp_path, "tasks.jsonl", [task])
        result = load_tasks(path)
        assert len(result) == 1
        assert result[0]["id"] == 42

    def test_tasks_preserve_all_fields(self, tmp_path):
        task = {
            "id": "task-extra",
            "description": "Task with extra fields",
            "command": "echo test",
            "expected_output": "test",
            "extra_field": "preserved",
            "nested": {"key": "value"},
        }
        path = _write_jsonl(tmp_path, "tasks.jsonl", [task])
        result = load_tasks(path)
        assert result[0]["extra_field"] == "preserved"
        assert result[0]["nested"] == {"key": "value"}


# ---------------------------------------------------------------------------
# File handling tests
# ---------------------------------------------------------------------------


class TestFileHandling:
    """File-not-found and invalid path handling."""

    def test_file_not_found_raises(self, tmp_path):
        nonexistent = str(tmp_path / "does_not_exist.jsonl")
        with pytest.raises(FileNotFoundError, match="not found"):
            load_tasks(nonexistent)

    def test_directory_path_raises(self, tmp_path):
        with pytest.raises(ValueError, match="not a file"):
            load_tasks(str(tmp_path))

    def test_empty_file_returns_empty_list(self, tmp_path):
        path = _write_raw_lines(tmp_path, "empty.jsonl", [""])
        result = load_tasks(path)
        assert result == []

    def test_blank_lines_are_skipped(self, tmp_path):
        path = _write_raw_lines(
            tmp_path,
            "blanks.jsonl",
            ["", json.dumps(_valid_task()), "", json.dumps(_valid_task("task-02")), ""],
        )
        result = load_tasks(path)
        assert len(result) == 2
        assert result[0]["id"] == "task-01"
        assert result[1]["id"] == "task-02"

    def test_whitespace_only_lines_are_skipped(self, tmp_path):
        path = _write_raw_lines(
            tmp_path,
            "whitespace.jsonl",
            ["   ", json.dumps(_valid_task()), "\t", "  \t  "],
        )
        result = load_tasks(path)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Invalid JSON handling
# ---------------------------------------------------------------------------


class TestInvalidJson:
    """Malformed JSON produces clear ValueError messages with line numbers."""

    def test_invalid_json_on_first_line(self, tmp_path):
        path = _write_raw_lines(tmp_path, "bad.jsonl", ["not json at all"])
        with pytest.raises(ValueError, match="Invalid JSON on line 1"):
            load_tasks(path)

    def test_invalid_json_with_line_number(self, tmp_path):
        path = _write_raw_lines(
            tmp_path,
            "bad.jsonl",
            [
                json.dumps(_valid_task()),
                '{"bad": }',
            ],
        )
        with pytest.raises(ValueError, match="Invalid JSON on line 2"):
            load_tasks(path)

    def test_trailing_comma_json_error(self, tmp_path):
        path = _write_raw_lines(
            tmp_path,
            "bad.jsonl",
            [
                json.dumps(_valid_task()),
                '{"id": "x", "bad": [],}',
            ],
        )
        with pytest.raises(ValueError, match="Invalid JSON on line 2"):
            load_tasks(path)

    def test_unclosed_object_json_error(self, tmp_path):
        path = _write_raw_lines(
            tmp_path,
            "bad.jsonl",
            [
                '{"id": "x", "description": "unfinished"',
            ],
        )
        with pytest.raises(ValueError, match="Invalid JSON on line 1"):
            load_tasks(path)

    def test_json_decode_error_chains_original_exception(self, tmp_path):
        path = _write_raw_lines(tmp_path, "bad.jsonl", ["{bad}"])
        with pytest.raises(ValueError) as exc_info:
            load_tasks(path)
        assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)

    def test_non_dict_json_object_raises(self, tmp_path):
        path = _write_raw_lines(
            tmp_path,
            "bad.jsonl",
            [
                json.dumps(_valid_task()),
                "[1, 2, 3]",
            ],
        )
        with pytest.raises(ValueError, match="Line 2: Expected JSON object, got list"):
            load_tasks(path)

    def test_json_string_raises(self, tmp_path):
        path = _write_raw_lines(
            tmp_path,
            "bad.jsonl",
            ['"just a string"'],
        )
        with pytest.raises(ValueError, match="Line 1: Expected JSON object, got str"):
            load_tasks(path)

    def test_json_number_raises(self, tmp_path):
        path = _write_raw_lines(
            tmp_path,
            "bad.jsonl",
            ["42"],
        )
        with pytest.raises(ValueError, match="Line 1: Expected JSON object, got int"):
            load_tasks(path)


# ---------------------------------------------------------------------------
# Validation error handling
# ---------------------------------------------------------------------------


class TestValidationErrors:
    """Tasks that fail validation produce clear ValueError messages with line numbers."""

    @pytest.mark.parametrize(
        "missing_key",
        ["id", "description", "command", "expected_output"],
    )
    def test_missing_required_field(self, tmp_path, missing_key):
        task = _valid_task()
        del task[missing_key]
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(
            ValueError, match=f"Line 1: Missing required fields: .*{missing_key}"
        ):
            load_tasks(path)

    def test_multiple_missing_required_fields(self, tmp_path):
        task = {
            "id": "task-01",
        }
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(
            ValueError,
            match="Line 1: Missing required fields: .*command.*description.*expected_output",
        ):
            load_tasks(path)

    def test_wrong_type_for_id(self, tmp_path):
        task = _valid_task()
        task["id"] = ["bad"]
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(
            ValueError, match="Line 1: 'id' must be a string or integer"
        ):
            load_tasks(path)

    def test_wrong_type_for_description(self, tmp_path):
        task = _valid_task()
        task["description"] = 123
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(ValueError, match="Line 1: 'description' must be a string"):
            load_tasks(path)

    def test_wrong_type_for_command(self, tmp_path):
        task = _valid_task()
        task["command"] = {"cmd": "bad"}
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(ValueError, match="Line 1: 'command' must be a string"):
            load_tasks(path)

    def test_wrong_type_for_expected_output(self, tmp_path):
        task = _valid_task()
        task["expected_output"] = None
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(
            ValueError, match="Line 1: 'expected_output' must be a string"
        ):
            load_tasks(path)

    def test_empty_id_raises(self, tmp_path):
        task = _valid_task()
        task["id"] = ""
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(ValueError, match="Line 1: 'id' cannot be empty"):
            load_tasks(path)

    def test_empty_description_raises(self, tmp_path):
        task = _valid_task()
        task["description"] = ""
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(ValueError, match="Line 1: 'description' cannot be empty"):
            load_tasks(path)

    def test_empty_command_raises(self, tmp_path):
        task = _valid_task()
        task["command"] = ""
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(ValueError, match="Line 1: 'command' cannot be empty"):
            load_tasks(path)

    def test_empty_expected_output_raises(self, tmp_path):
        task = _valid_task()
        task["expected_output"] = ""
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(
            ValueError, match="Line 1: 'expected_output' cannot be empty"
        ):
            load_tasks(path)

    def test_validation_error_on_line_3(self, tmp_path):
        tasks = [
            _valid_task("task-01"),
            _valid_task("task-02"),
            {"bad": "task"},
        ]
        path = _write_jsonl(tmp_path, "bad.jsonl", tasks)
        with pytest.raises(ValueError, match="Line 3: Missing required fields"):
            load_tasks(path)

    def test_validation_error_chains_original_exception(self, tmp_path):
        task = {"id": ""}  # Will fail required fields + empty id
        path = _write_jsonl(tmp_path, "bad.jsonl", [task])
        with pytest.raises(ValueError) as exc_info:
            load_tasks(path)
        assert isinstance(exc_info.value.__cause__, ValidationError)


# ---------------------------------------------------------------------------
# End-to-end workflow tests
# ---------------------------------------------------------------------------


class TestEndToEndWorkflow:
    """Realistic multi-task workflows with mixed valid and complex data."""

    def test_full_workflow_loads_and_validates(self, tmp_path):
        tasks = [
            {
                "id": "setup",
                "description": "Setup environment",
                "command": "mkdir -p /tmp/test",
                "expected_output": "ok",
            },
            {
                "id": "run-001",
                "description": "Run first benchmark",
                "command": "python benchmark.py --task 1",
                "expected_output": "PASS",
            },
            {
                "id": "run-002",
                "description": "Run second benchmark",
                "command": "python benchmark.py --task 2",
                "expected_output": "PASS",
            },
            {
                "id": "cleanup",
                "description": "Clean up temp files",
                "command": "rm -rf /tmp/test",
                "expected_output": "done",
            },
        ]
        path = _write_jsonl(tmp_path, "workflow.jsonl", tasks)
        result = load_tasks(path)
        assert len(result) == 4
        assert result[0]["id"] == "setup"
        assert result[1]["command"] == "python benchmark.py --task 1"
        assert result[2]["expected_output"] == "PASS"
        assert result[3]["description"] == "Clean up temp files"

    def test_workflow_with_empty_outputs_raises_error(self, tmp_path):
        tasks = [
            {
                "id": "empty-output-test",
                "description": "Test empty output",
                "command": ":",
                "expected_output": "",
            },
        ]
        path = _write_jsonl(tmp_path, "workflow.jsonl", tasks)
        with pytest.raises(ValueError, match="'expected_output' cannot be empty"):
            load_tasks(path)

    def test_workflow_with_unicode_content(self, tmp_path):
        tasks = [
            {
                "id": "unicode-test",
                "description": "Unicode chars: 你好 мир 🌍",
                "command": "echo 'hello мир'",
                "expected_output": "hello мир",
            },
        ]
        path = _write_jsonl(tmp_path, "unicode.jsonl", tasks)
        result = load_tasks(path)
        assert len(result) == 1
        assert result[0]["description"] == "Unicode chars: 你好 мир 🌍"

    def test_workflow_preserves_task_order(self, tmp_path):
        tasks = [
            {
                "id": str(i),
                "description": f"Task {i}",
                "command": f"cmd {i}",
                "expected_output": f"out {i}",
            }
            for i in range(100)
        ]
        path = _write_jsonl(tmp_path, "large.jsonl", tasks)
        result = load_tasks(path)
        assert len(result) == 100
        for i, task in enumerate(result):
            assert task["id"] == str(i)
            assert task["description"] == f"Task {i}"

    def test_realistic_jsonl_with_comments_in_strings(self, tmp_path):
        task = {
            "id": "comment-test",
            "description": "Task with /* comment-like */ text and // slashes",
            "command": "echo 'special chars: /* not a comment */ // not one either'",
            "expected_output": "special chars: /* not a comment */ // not one either",
        }
        path = _write_jsonl(tmp_path, "comments.jsonl", [task])
        result = load_tasks(path)
        assert len(result) == 1
        assert "comment-like" in result[0]["description"]
        assert "// slashes" in result[0]["description"]

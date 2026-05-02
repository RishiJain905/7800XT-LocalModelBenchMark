# -*- coding: utf-8 -*-
"""Benchmark suite registry — discovers and describes available benchmark suites."""

from __future__ import annotations

import copy
import os.path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

_SUITES_YAML_PATH = "benchmarks/suites.yaml"

# Internal cache populated on first call
_suites_cache: list[dict[str, Any]] | None = None


def _resolve_path(path: str) -> str:
    """Resolve a relative path against the project root."""
    return os.path.normpath(path)


def _load_suites() -> list[dict[str, Any]]:
    """Load and validate suites from the YAML registry file.

    Returns the list of suite dicts.
    Raises FileNotFoundError if the YAML file does not exist.
    Raises ValueError if the YAML is malformed or a task_file is missing.
    """
    path = _resolve_path(_SUITES_YAML_PATH)

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Suite registry not found: {path}. "
            f"Expected a suites.yaml file at {_SUITES_YAML_PATH}."
        )

    if yaml is None:
        raise ImportError("PyYAML is required to load suite registry.")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "suites" not in data:
        raise ValueError(
            f"Invalid suite registry: expected a YAML file with a top-level 'suites' key. "
            f"Found type: {type(data).__name__}."
        )

    suites: list[dict[str, Any]] = data["suites"]
    _validate_suites(suites)
    return suites


_REQUIRED_SUITE_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "name",
        "category",
        "task_file",
        "description",
        "scoring",
    }
)


def _validate_suites(suites: list[dict[str, Any]]) -> None:
    """Validate each suite entry has required fields and valid task_file paths."""
    if not isinstance(suites, list):
        raise ValueError(
            f"Invalid suite registry: 'suites' must be a list, got {type(suites).__name__}."
        )

    seen_ids: set[str] = set()
    for i, suite in enumerate(suites):
        if not isinstance(suite, dict):
            raise ValueError(
                f"Suite at index {i}: expected a dict, got {type(suite).__name__}."
            )

        missing = _REQUIRED_SUITE_FIELDS - set(suite.keys())
        if missing:
            raise ValueError(
                f"Suite at index {i} (id={suite.get('id', '?')}): "
                f"missing required fields: {', '.join(sorted(missing))}."
            )

        sid: str = suite["id"]
        if sid in seen_ids:
            raise ValueError(f"Duplicate suite id: {sid}.")
        seen_ids.add(sid)

        # Validate task_file exists on disk
        task_path = _resolve_path(suite["task_file"])
        if not os.path.isfile(task_path):
            raise ValueError(
                f"Suite '{sid}': task_file not found at {task_path}. "
                f"Expected the JSONL file to exist before registering the suite."
            )


def list_suites() -> list[dict[str, Any]]:
    """Return all available benchmark suites.

    Each suite dict contains: id, name, category, task_file, description, scoring.

    Raises FileNotFoundError or ValueError on invalid registry state.
    """
    global _suites_cache
    if _suites_cache is None:
        _suites_cache = _load_suites()
    return copy.deepcopy(_suites_cache)


def get_suite(suite_id: str) -> dict[str, Any]:
    """Return a single suite by its id.

    Raises KeyError if the suite_id is not found.
    Raises FileNotFoundError or ValueError on invalid registry state.
    """
    suites = list_suites()
    for suite in suites:
        if suite["id"] == suite_id:
            return dict(suite)
    raise KeyError(
        f"Suite not found: '{suite_id}'. Available suites: {[s['id'] for s in suites]}."
    )


def clear_cache() -> None:
    """Clear the internal suite cache. Used in testing."""
    global _suites_cache
    _suites_cache = None

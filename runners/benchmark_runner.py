"""Core benchmark runner — reusable benchmark execution loop.

Exposed API:
    run_benchmark(config, tasks, options, progress_callback=None, result_callback=None) -> dict

Internal helpers (extracted from the root ``run_benchmark.py`` CLI):
    _resolve_scorer, _build_result, _build_error_result, _extract_settings,
    CATEGORY_SCORER_MAP
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable

from runners.llama_client import run_prompt
from runners.result_writer import save_artifact
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


class BenchmarkCancelled(Exception):
    """Raised when a benchmark run is explicitly cancelled."""


def _resolve_scorer(task: dict[str, Any]) -> str:
    """Map a task's category to the appropriate scorer name."""
    category: str = task.get("metadata", {}).get("category", "")
    return CATEGORY_SCORER_MAP.get(category, _FALLBACK_SCORER)


def _extract_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Extract tracked model settings from the config dictionary."""
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
    """Build a successful per-attempt result dictionary."""
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
        "artifact_paths": [],
    }


def _build_error_result(
    task: dict[str, Any],
    config: dict[str, Any],
    error: str,
    task_file: str,
    run_id: str,
) -> dict[str, Any]:
    """Build an error per-attempt result dictionary when ``run_prompt`` raises."""
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
        "artifact_paths": [],
    }


def run_benchmark(
    config: dict[str, Any],
    tasks: list[dict[str, Any]],
    options: dict[str, Any],
    progress_callback: Callable[[int, int], None] | None = None,
    result_callback: Callable[[dict[str, Any]], None] | None = None,
    cancel_callback: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Run a benchmark across the given tasks with the supplied config.

    Parameters
    ----------
    config : dict
        Validated model configuration dictionary.
    tasks : list[dict]
        Task dictionaries loaded from a JSONL task file.
    options : dict
        Supported keys:

        - ``repeats`` (int, default 1): number of times to repeat each task.
        - ``dry_run`` (bool, default False): if ``True``, no model calls are made.
        - ``task_file`` (str): path to the task file (for result metadata).
        - ``run_id`` (str | None): if provided, used as-is; otherwise
          auto-generated as ``YYYY-MM-DD_HH-MM-SS_<uuid8>``.
    progress_callback : callable | None
        Called after every attempt with ``(completed_attempts, total_attempts)``.
    result_callback : callable | None
        Called after every attempt with the per-attempt result dict.

    Returns
    -------
    dict
        Summary dictionary with keys: ``results``, ``run_id``, ``total_tasks``,
        ``total_attempts``, ``passed``, ``failed``, ``average_score``,
        ``average_latency_sec``.
    """
    repeats: int = options.get("repeats", 1)
    dry_run: bool = options.get("dry_run", False)
    task_file: str = options.get("task_file", "")
    run_id: str = options.get("run_id") or (
        datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{uuid.uuid4().hex[:8]}"
    )

    total_tasks = len(tasks)
    total_attempts = total_tasks * repeats

    if dry_run:
        if progress_callback:
            progress_callback(total_tasks, total_tasks)
        return {
            "results": [],
            "run_id": run_id,
            "total_tasks": total_tasks,
            "total_attempts": total_attempts,
            "passed": 0,
            "failed": 0,
            "average_score": 0.0,
            "average_latency_sec": 0.0,
        }

    results: list[dict[str, Any]] = []

    for task in tasks:
        scorer_name = _resolve_scorer(task)
        for repeat_idx in range(repeats):
            if cancel_callback and cancel_callback():
                raise BenchmarkCancelled("Benchmark run was cancelled.")

            prompt: str = task["description"]
            try:
                model_result = run_prompt(config, prompt)
                scorer = get_scorer(scorer_name)
                score_result = scorer(task, model_result["response"])
                result = _build_result(
                    task, config, model_result, score_result, task_file, run_id
                )
            except (KeyboardInterrupt, BenchmarkCancelled):
                raise
            except Exception as exc:
                result = _build_error_result(task, config, str(exc), task_file, run_id)

            # Save coding artifact if applicable
            if task.get("metadata", {}).get("category") == "code":
                run_dir = options.get("run_dir")
                if run_dir is not None:
                    suite_id = options.get("suite_id", "")
                    response_text = result.get("response", "")
                    if response_text:
                        artifact_path = save_artifact(
                            run_dir, suite_id, task, response_text
                        )
                        result["artifact_paths"].append(artifact_path)

            result["repeat_index"] = repeat_idx
            result["repeat_count"] = repeats
            results.append(result)

            if progress_callback:
                progress_callback(len(results), total_attempts)
            if result_callback:
                result_callback(result)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    avg_score = sum(r["score"] for r in results) / total if total else 0.0
    avg_latency = sum(r["latency_sec"] for r in results) / total if total else 0.0

    return {
        "results": results,
        "run_id": run_id,
        "total_tasks": total_tasks,
        "total_attempts": total_attempts,
        "passed": passed,
        "failed": failed,
        "average_score": avg_score,
        "average_latency_sec": avg_latency,
    }

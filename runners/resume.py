"""Helpers for resuming incomplete structured benchmark runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runners.task_loader import load_tasks

RESUMABLE_STATUSES = {"running", "cancelled", "failed"}


@dataclass(frozen=True)
class ResumeState:
    run_dir: Path
    manifest: dict[str, Any]
    completed_results: list[dict[str, Any]]
    completed_attempts: set[tuple[str, int]]
    tasks: list[dict[str, Any]]
    repeats: int
    total_attempts: int
    config_id: str
    suite_info: dict[str, str] | None
    warnings: list[str]


def read_raw_results(
    run_dir: str | Path,
    *,
    strict: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Read valid raw result records from a run folder."""
    raw_path = Path(run_dir) / "raw.jsonl"
    if not raw_path.is_file():
        raise FileNotFoundError(f"Raw results file not found: {raw_path}")

    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    with raw_path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                message = f"raw.jsonl line {line_number}: {exc.msg}"
                if strict:
                    raise ValueError(message) from exc
                warnings.append(message)
                continue

            if not isinstance(record, dict):
                message = f"raw.jsonl line {line_number}: expected JSON object"
                if strict:
                    raise ValueError(message)
                warnings.append(message)
                continue

            results.append(record)

    return results, warnings


def completed_attempt_key(result: dict[str, Any]) -> tuple[str, int] | None:
    """Return the resume key for a raw result, or None if it is incomplete."""
    task_id = result.get("task_id")
    repeat_index = result.get("repeat_index")
    if task_id is None or repeat_index is None:
        return None

    try:
        return str(task_id), int(repeat_index)
    except (TypeError, ValueError):
        return None


def load_resume_state(run_dir: str | Path, *, strict: bool = False) -> ResumeState:
    """Load manifest, raw results, tasks, and completed attempt keys."""
    resolved_run_dir = Path(run_dir).resolve()
    manifest_path = resolved_run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if not isinstance(manifest, dict):
        raise ValueError(f"Manifest must contain a JSON object: {manifest_path}")

    task_file = manifest.get("task_file")
    if not task_file:
        raise ValueError("Manifest is missing required field: task_file")

    config_id = manifest.get("model_config_id")
    if not config_id:
        raise ValueError("Manifest is missing required field: model_config_id")

    completed_results, warnings = read_raw_results(resolved_run_dir, strict=strict)
    tasks = load_tasks(str(task_file))
    repeats = int(
        manifest.get("repeats") or _infer_repeats(manifest, len(tasks), completed_results)
    )
    total_attempts = len(tasks) * repeats

    completed_attempts: set[tuple[str, int]] = set()
    for index, result in enumerate(completed_results, start=1):
        key = completed_attempt_key(result)
        if key is None:
            warnings.append(
                f"raw.jsonl record {index}: missing task_id or repeat_index; ignored for resume"
            )
            continue
        completed_attempts.add(key)

    suite_info = None
    if manifest.get("suite_id") or manifest.get("suite_name"):
        suite_info = {
            "id": str(manifest.get("suite_id", "")),
            "name": str(manifest.get("suite_name", "")),
        }

    return ResumeState(
        run_dir=resolved_run_dir,
        manifest=manifest,
        completed_results=completed_results,
        completed_attempts=completed_attempts,
        tasks=tasks,
        repeats=repeats,
        total_attempts=total_attempts,
        config_id=str(config_id),
        suite_info=suite_info,
        warnings=warnings,
    )


def list_resumable_runs(results_root: str | Path = "results/runs") -> list[dict[str, Any]]:
    """List run folders whose manifests indicate incomplete status."""
    root = Path(results_root)
    if not root.exists():
        return []

    runs: list[dict[str, Any]] = []
    for manifest_path in root.glob("*/*/manifest.json"):
        try:
            with manifest_path.open("r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(manifest, dict):
            continue

        status = manifest.get("status")
        if status not in RESUMABLE_STATUSES:
            continue

        run_dir = manifest_path.parent.resolve()
        runs.append(
            {
                "run_dir": str(run_dir),
                "run_id": manifest.get("run_id", run_dir.name),
                "model_config_id": manifest.get("model_config_id", run_dir.parent.name),
                "status": status,
                "task_file": manifest.get("task_file", ""),
                "started_at": manifest.get("started_at", ""),
            }
        )

    return sorted(runs, key=lambda item: (item["status"], item["run_dir"]))


def _infer_repeats(
    manifest: dict[str, Any],
    total_tasks: int,
    completed_results: list[dict[str, Any]],
) -> int:
    raw_repeat_counts = [
        result.get("repeat_count")
        for result in completed_results
        if isinstance(result.get("repeat_count"), int)
    ]
    if raw_repeat_counts:
        return max(1, max(raw_repeat_counts))

    total_attempts = manifest.get("total_attempts")
    if isinstance(total_attempts, int) and total_tasks:
        return max(1, total_attempts // total_tasks)
    return 1

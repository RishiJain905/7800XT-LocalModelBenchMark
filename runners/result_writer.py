"""Result writer for persisting benchmark results to disk."""

from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from statistics import mean

VALID_RUN_STATUSES = {"running", "completed", "cancelled", "failed"}


def create_run_folder(model_config_id: str, run_id: str) -> Path:
    """Create the structured per-run folder and placeholder files."""
    run_dir = Path("results") / "runs" / model_config_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(exist_ok=True)
    (run_dir / "manifest.json").touch(exist_ok=True)
    (run_dir / "raw.jsonl").touch(exist_ok=True)
    (run_dir / "summary.json").touch(exist_ok=True)
    return run_dir.resolve()


def build_manifest(
    config: dict,
    task_file: str,
    run_id: str,
    status: str,
    started_at: str,
    completed_at: str | None = None,
    suite_info: dict | None = None,
) -> dict:
    """Build the manifest payload for a structured benchmark run."""
    _validate_run_status(status)

    manifest = {
        "run_id": run_id,
        "model_config_id": config["id"],
        "model_name": config.get("model_name", ""),
        "task_file": task_file,
        "server_url": config.get("runtime", {}).get("server_url", ""),
        "settings": config.get("settings", {}),
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
    }

    if suite_info:
        manifest["suite_id"] = suite_info.get("id", "")
        manifest["suite_name"] = suite_info.get("name", "")

    return manifest


def write_manifest(run_dir: str | Path, manifest: dict) -> str:
    """Write a run manifest as pretty JSON."""
    path = Path(run_dir) / "manifest.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)
        fh.write("\n")
    return str(path.resolve())


def update_manifest_status(
    run_dir: str | Path,
    status: str,
    completed_at: str | None = None,
) -> str:
    """Update the status fields in an existing manifest."""
    _validate_run_status(status)
    path = Path(run_dir) / "manifest.json"
    with path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    manifest["status"] = status
    if completed_at is not None:
        manifest["completed_at"] = completed_at

    return write_manifest(run_dir, manifest)


def write_run_raw_results(run_dir: str | Path, results: list[dict]) -> str:
    """Write structured raw results to ``raw.jsonl`` inside a run folder."""
    path = Path(run_dir) / "raw.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result, default=str) + "\n")
    return str(path.resolve())


def append_run_raw_result(run_dir: str | Path, result: dict) -> str:
    """Append one completed attempt to ``raw.jsonl`` and force it to disk."""
    path = Path(run_dir) / "raw.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return str(path.resolve())


def write_run_summary(
    run_dir: str | Path,
    summary: dict,
    config: dict,
    task_file: str,
    status: str,
    repeats: int = 1,
    suite_info: dict | None = None,
) -> str:
    """Write aggregate run metadata to ``summary.json`` inside a run folder."""
    _validate_run_status(status)
    total_attempts = summary.get("total_attempts", 0)
    passed = summary.get("passed", 0)
    payload = {
        "run_id": summary["run_id"],
        "model_config_id": config["id"],
        "model_name": config.get("model_name", ""),
        "task_file": task_file,
        "run_folder": str(Path(run_dir).resolve()),
        "status": status,
        "total_tasks": summary.get("total_tasks", 0),
        "total_attempts": total_attempts,
        "passed": passed,
        "failed": summary.get("failed", total_attempts - passed),
        "pass_rate": passed / total_attempts if total_attempts else 0.0,
        "average_score": summary.get("average_score", 0.0),
        "average_latency_sec": summary.get("average_latency_sec", 0.0),
        "repeats": repeats,
    }

    if suite_info:
        payload["suite_id"] = suite_info.get("id", "")
        payload["suite_name"] = suite_info.get("name", "")

    path = Path(run_dir) / "summary.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
        fh.write("\n")
    return str(path.resolve())


def _validate_run_status(status: str) -> None:
    """Validate run manifest status values."""
    if status not in VALID_RUN_STATUSES:
        allowed = ", ".join(sorted(VALID_RUN_STATUSES))
        raise ValueError(f"Invalid run status '{status}'. Expected one of: {allowed}.")


def write_raw_results(
    results: list[dict],
    model_config_id: str,
    task_file: str,
    run_id: str,
) -> str:
    """Write raw benchmark results to a JSONL file.

    Creates the necessary directory structure and writes one JSON object per
    line for each result in the list.

    Args:
        results: List of result dicts produced by the benchmark harness.
        model_config_id: Identifier for the model configuration (used as
            subdirectory name).
        task_file: Full path to the source task file, used to derive the
            output filename stem.
        run_id: Unique run identifier appended to the filename.

    Returns:
        Absolute path (as a string) to the written JSONL file.
    """
    stem = Path(task_file).stem
    output_dir = Path("results") / "raw" / model_config_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{stem}_{run_id}.jsonl"

    with open(output_path, "w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result, default=str) + "\n")

    return str(output_path.resolve())


def append_summary(
    results: list[dict],
    model_config_id: str,
    task_file: str,
    run_id: str,
    repeats: int = 1,
    total_tasks: int | None = None,
) -> str:
    """Append a summary row to the results/summary.csv file.

    Computes aggregate statistics (pass rate, average score, average latency)
    from the given result list and writes a single CSV row.  Creates the
    header row automatically when the file does not yet exist.

    Args:
        results: List of result dicts produced by the benchmark harness.
        model_config_id: Identifier for the model configuration.
        task_file: Full path to the source task file (stored as-is).
        run_id: Unique run identifier.
        repeats: Number of repeat runs per task (default: 1).
        total_tasks: Number of unique task definitions. If None, derived from
            results and repeats.

    Returns:
        Absolute path (as a string) to the summary CSV file.
    """
    summary_dir = Path("results")
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_path = summary_dir / "summary.csv"

    if total_tasks is None:
        total_tasks = len(results) // repeats if repeats else len(results)

    total_attempts = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total_attempts - passed
    pass_rate = passed / total_attempts if total_attempts else 0.0
    average_score = mean(r["score"] for r in results) if results else 0.0
    average_latency_sec = mean(r["latency_sec"] for r in results) if results else 0.0

    fieldnames = [
        "run_id",
        "model_config_id",
        "task_file",
        "total_tasks",
        "total_attempts",
        "passed",
        "failed",
        "pass_rate",
        "average_score",
        "average_latency_sec",
        "repeats",
    ]

    file_exists = summary_path.exists()

    if file_exists and summary_path.stat().st_size > 0:
        with open(summary_path, "r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            existing_fieldnames = reader.fieldnames

        if existing_fieldnames and existing_fieldnames != fieldnames:
            old_rows: list[dict[str, str]] = []
            with open(summary_path, "r", newline="", encoding="utf-8") as fh:
                old_rows = list(csv.DictReader(fh))

            with open(summary_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(
                    fh, fieldnames=fieldnames, extrasaction="ignore"
                )
                writer.writeheader()
                for row in old_rows:
                    writer.writerow(row)
                writer.writerow(
                    {
                        "run_id": run_id,
                        "model_config_id": model_config_id,
                        "task_file": task_file,
                        "total_tasks": total_tasks,
                        "total_attempts": total_attempts,
                        "passed": passed,
                        "failed": failed,
                        "pass_rate": f"{pass_rate:.4f}",
                        "average_score": f"{average_score:.4f}",
                        "average_latency_sec": f"{average_latency_sec:.3f}",
                        "repeats": repeats,
                    }
                )

            return str(summary_path.resolve())

    with open(summary_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "run_id": run_id,
                "model_config_id": model_config_id,
                "task_file": task_file,
                "total_tasks": total_tasks,
                "total_attempts": total_attempts,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{pass_rate:.4f}",
                "average_score": f"{average_score:.4f}",
                "average_latency_sec": f"{average_latency_sec:.3f}",
                "repeats": repeats,
            }
        )

    return str(summary_path.resolve())


def sanitize_filename(name: str) -> str:
    """Replace any character that is NOT alphanumeric, hyphen, underscore, or period with an underscore."""
    return re.sub(r"[^a-zA-Z0-9\-_.]", "_", name)


def save_artifact(run_dir: str | Path, suite_id: str, task: dict, response: str) -> str:
    """Save a model-generated coding artifact to disk.

    Args:
        run_dir: The run directory (contains an ``artifacts/`` subfolder).
        suite_id: Suite identifier (e.g. ``"coding.frontend"``).
        task: Task dictionary (must contain ``"id"`` and may contain
            ``metadata.artifact_extension``).
        response: The model response text to write.

    Returns:
        Absolute path (as a string) to the written artifact file.
    """
    run_dir = Path(run_dir)
    task_id = task["id"]
    sanitized_id = sanitize_filename(task_id)
    extension = task.get("metadata", {}).get("artifact_extension", ".md")

    artifacts_dir = run_dir / "artifacts" / suite_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    file_path = artifacts_dir / f"{sanitized_id}_response{extension}"
    with file_path.open("w", encoding="utf-8") as fh:
        fh.write(response)

    return str(file_path.resolve())

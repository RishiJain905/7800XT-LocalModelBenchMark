"""Result writer for persisting benchmark results to disk."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean


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

    Returns:
        Absolute path (as a string) to the summary CSV file.
    """
    summary_dir = Path("results")
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_path = summary_dir / "summary.csv"

    total_tasks = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total_tasks - passed
    pass_rate = passed / total_tasks if total_tasks else 0.0
    average_score = mean(r["score"] for r in results) if results else 0.0
    average_latency_sec = mean(r["latency_sec"] for r in results) if results else 0.0

    fieldnames = [
        "run_id",
        "model_config_id",
        "task_file",
        "total_tasks",
        "passed",
        "failed",
        "pass_rate",
        "average_score",
        "average_latency_sec",
    ]

    file_exists = summary_path.exists()

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
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{pass_rate:.4f}",
                "average_score": f"{average_score:.4f}",
                "average_latency_sec": f"{average_latency_sec:.3f}",
            }
        )

    return str(summary_path.resolve())

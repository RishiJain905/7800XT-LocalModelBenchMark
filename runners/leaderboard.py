"""Leaderboard generator for benchmark summary results."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path


def generate_leaderboard(
    summary_csv_path: str = "results/summary.csv",
    output_path: str = "results/reports/leaderboard.md",
) -> str:
    """Generate a Markdown leaderboard from the benchmark summary CSV.

    Reads the summary CSV, deduplicates rows keeping only the most recent
    run for each ``(model_config_id, task_file)`` pair, then writes a sorted
    Markdown leaderboard table to disk.

    Args:
        summary_csv_path: Path to the summary CSV file produced by the
            benchmark harness.
        output_path: Destination filesystem path for the leaderboard Markdown
            file.  Parent directories are created automatically.

    Returns:
        Absolute path (as a resolved string) to the written leaderboard file.
        If the CSV is missing or empty, a minimal ``"No data yet."``
        leaderboard is still written and its path returned.
    """
    csv_path = Path(summary_csv_path)
    out_path = Path(output_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Missing CSV ---
    if not csv_path.exists():
        print(
            f"WARNING: Summary CSV not found at {csv_path.resolve()}",
            file=sys.stderr,
        )
        _write_empty_leaderboard(out_path)
        return str(out_path.resolve())

    # --- Read & group rows ---
    grouped: defaultdict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)

            rows = list(reader)
            if not rows:
                _write_empty_leaderboard(out_path)
                return str(out_path.resolve())

            for row in rows:
                key = (row["model_config_id"], row["task_file"])
                grouped[key].append(row)
    except OSError as exc:
        print(f"ERROR: Failed to read summary CSV: {exc}", file=sys.stderr)
        _write_empty_leaderboard(out_path)
        return str(out_path.resolve())

    # --- Deduplicate: keep the most recent run_id per group ---
    latest_rows: list[dict[str, str]] = []
    for rows_list in grouped.values():
        latest = max(rows_list, key=lambda r: r["run_id"])
        latest_rows.append(latest)

    # --- Parse numeric fields ---
    parsed: list[dict] = []
    for row in latest_rows:
        parsed.append(
            {
                "model_config_id": row["model_config_id"],
                "task_file": row["task_file"],
                "total_tasks": int(row["total_tasks"]),
                "total_attempts": int(row.get("total_attempts", row["total_tasks"])),
                "repeats": int(row.get("repeats", "1")),
                "pass_rate": float(row["pass_rate"]),
                "average_score": float(row["average_score"]),
                "average_latency_sec": float(row["average_latency_sec"]),
            }
        )

    # --- Sort ---
    parsed.sort(
        key=lambda r: (
            -r["average_score"],
            -r["pass_rate"],
            r["average_latency_sec"],
        )
    )

    # --- Render Markdown ---
    lines: list[str] = [
        "# Local Model Benchmark Leaderboard",
        "",
        (
            "| Model Config | Task File | Total Tasks | Total Attempts | Repeats "
            "| Pass Rate | Avg Score | Avg Latency |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in parsed:
        lines.append(
            f"| {row['model_config_id']} | {row['task_file']} | "
            f"{row['total_tasks']} | {row['total_attempts']} | "
            f"{row['repeats']} | "
            f"{row['pass_rate'] * 100:.1f}% | "
            f"{row['average_score']:.2f} | {row['average_latency_sec']:.2f}s |"
        )

    lines.append("")  # trailing newline

    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    except OSError as exc:
        print(f"ERROR: Failed to write leaderboard: {exc}", file=sys.stderr)

    return str(out_path.resolve())


def _write_empty_leaderboard(out_path: Path) -> None:
    """Write a minimal ``"No data yet."`` leaderboard file.

    Args:
        out_path: Destination filesystem path for the leaderboard file.
    """
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("# Local Model Benchmark Leaderboard\n\nNo data yet.\n")
    except OSError as exc:
        print(
            f"ERROR: Failed to write leaderboard: {exc}",
            file=sys.stderr,
        )

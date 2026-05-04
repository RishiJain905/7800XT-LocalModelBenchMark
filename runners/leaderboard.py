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
    run for each model/suite pair when suite metadata exists, then writes
    suite-grouped Markdown leaderboard tables to disk.

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
                key = _dedupe_key(row)
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
                "suite_id": row.get("suite_id", ""),
                "suite_name": row.get("suite_name", ""),
                "task_file": row["task_file"],
                "status": row.get("status", ""),
                "total_tasks": int(row["total_tasks"]),
                "total_attempts": int(row.get("total_attempts", row["total_tasks"])),
                "repeats": int(row.get("repeats", "1")),
                "pass_rate": float(row["pass_rate"]),
                "average_score": float(row["average_score"]),
                "average_latency_sec": float(row["average_latency_sec"]),
            }
        )

    # --- Render Markdown ---
    lines: list[str] = [
        "# Local Model Benchmark Leaderboard",
        "",
    ]

    by_suite: defaultdict[str, list[dict]] = defaultdict(list)
    for row in parsed:
        by_suite[_suite_group_label(row)].append(row)

    for suite_label in sorted(by_suite):
        lines.extend(
            [
                f"## {suite_label}",
                "",
                (
                    "| Model Config | Suite | Task File | Status | Total Attempts "
                    "| Pass Rate | Avg Score | Avg Latency |"
                ),
                "|---|---|---|---|---:|---:|---:|---:|",
            ]
        )
        suite_rows = sorted(by_suite[suite_label], key=_rank_key)
        for row in suite_rows:
            suite = _suite_display(row)
            lines.append(
                f"| {row['model_config_id']} | {suite} | {row['task_file']} | "
                f"{row['status']} | {row['total_attempts']} | "
                f"{row['pass_rate'] * 100:.1f}% | "
                f"{row['average_score']:.2f} | {row['average_latency_sec']:.2f}s |"
            )
        lines.append("")

    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    except OSError as exc:
        print(f"ERROR: Failed to write leaderboard: {exc}", file=sys.stderr)

    return str(out_path.resolve())


def _dedupe_key(row: dict[str, str]) -> tuple[str, str]:
    """Dedupe by model/suite for Task 16 rows, otherwise model/task file."""
    suite_id = row.get("suite_id", "")
    if suite_id:
        return (row["model_config_id"], suite_id)
    return (row["model_config_id"], row["task_file"])


def _rank_key(row: dict) -> tuple[float, float, float]:
    """Sort by score desc, pass rate desc, latency asc."""
    return (-row["average_score"], -row["pass_rate"], row["average_latency_sec"])


def _suite_display(row: dict) -> str:
    """Return a compact suite label for a leaderboard row."""
    if row["suite_id"] and row["suite_name"]:
        return f"{row['suite_id']} ({row['suite_name']})"
    return row["suite_id"] or "legacy"


def _suite_group_label(row: dict) -> str:
    """Group suite rows by suite; legacy rows fall back to task file."""
    return _suite_display(row) if row["suite_id"] else row["task_file"]


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

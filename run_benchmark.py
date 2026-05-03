"""Local Model Benchmark Harness - orchestrates config loading, model prompting,
and scoring across a JSONL task file to produce per-task results and a summary.
Supports direct task files (--task-file) or named benchmark suites (--suite).
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime
from typing import Any

from runners.config_loader import load_config
from runners.leaderboard import generate_leaderboard
from runners.result_writer import (
    append_summary,
    build_manifest,
    create_run_folder,
    update_manifest_status,
    write_manifest,
    write_raw_results,
    write_run_raw_results,
    write_run_summary,
)
from runners.task_loader import load_tasks
from runners.suite_registry import get_suite
from runners.benchmark_runner import run_benchmark


def _resolve_config_path(config_arg: str) -> str:
    """Resolve --config argument to a filesystem path.

    If config_arg is an existing file path, use it directly (backward compat).
    Otherwise, treat it as a model ID and look it up via the model registry.
    """
    if os.path.isfile(config_arg):
        return config_arg
    # Treat as model ID — lookup and resolve to file path
    from runners.model_registry import get_model_config

    try:
        get_model_config(config_arg)  # validate it exists
    except KeyError:
        raise FileNotFoundError(
            f"Model config not found: '{config_arg}'. "
            f"Use a path to a .yaml file or a model ID from configs/models/."
        )
    # Resolve to the expected file path
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(
        os.path.join(here, "configs", "models", f"{config_arg}.yaml")
    )


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
        config_path = _resolve_config_path(args.config)
        config = load_config(config_path)
    except (FileNotFoundError, ValueError, KeyError) as exc:
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

    options: dict[str, Any] = {
        "repeats": args.repeats,
        "dry_run": args.dry_run,
        "task_file": task_file,
    }
    if suite_info:
        options["suite_id"] = suite_info["id"]
        options["suite_name"] = suite_info.get("name", "")

    if args.dry_run:
        # Keep exact same dry-run output format
        from runners.benchmark_runner import _resolve_scorer

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

    total_attempts = len(tasks) * args.repeats
    _counter_state = [1]

    def _print_result(result: dict[str, Any]) -> None:
        idx = _counter_state[0]
        _counter_state[0] += 1
        print(
            f"[{idx}/{total_attempts}] {result['task_id']}"
            f" (repeat {result['repeat_index'] + 1}/{args.repeats})  "
            f"score={result['score']}  "
            f"latency={result['latency_sec']:.2f}s"
        )

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{uuid.uuid4().hex[:8]}"
    options["run_id"] = run_id
    started_at = datetime.now().isoformat(timespec="seconds")
    run_dir = create_run_folder(config["id"], run_id)
    options["run_dir"] = str(run_dir)

    manifest = build_manifest(
        config,
        task_file,
        run_id,
        "running",
        started_at,
        suite_info=suite_info,
    )
    write_manifest(run_dir, manifest)

    try:
        summary = run_benchmark(
            config,
            tasks,
            options,
            result_callback=_print_result,
        )
    except Exception:
        update_manifest_status(
            run_dir,
            "failed",
            datetime.now().isoformat(timespec="seconds"),
        )
        raise

    flat_results = summary["results"]
    run_id = summary["run_id"]

    print()
    print(
        f"Total tasks: {summary['total_tasks']} "
        f"(repeats={args.repeats}, total_attempts={summary['total_attempts']})"
    )
    print(f"Passed: {summary['passed']}")
    print(f"Average score: {summary['average_score']:.2f}")
    print(f"Average latency: {summary['average_latency_sec']:.2f}s")

    try:
        raw_path = write_run_raw_results(run_dir, flat_results)
        write_run_summary(
            run_dir,
            summary,
            config,
            task_file,
            "completed",
            repeats=args.repeats,
            suite_info=suite_info,
        )
        update_manifest_status(
            run_dir,
            "completed",
            datetime.now().isoformat(timespec="seconds"),
        )
        print(f"Saved raw results to {raw_path}")
    except OSError as exc:
        print(f"Error writing raw results: {exc}", file=sys.stderr)

    try:
        write_raw_results(flat_results, config["id"], task_file, run_id)
    except OSError as exc:
        print(
            f"Error writing raw results compatibility copy: {exc}",
            file=sys.stderr,
        )

    try:
        summary_path = append_summary(
            flat_results,
            config["id"],
            task_file,
            run_id,
            repeats=args.repeats,
            total_tasks=summary["total_tasks"],
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

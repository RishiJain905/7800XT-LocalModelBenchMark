"""Local Model Benchmark Harness - orchestrates config loading, model prompting,
and scoring across a JSONL task file to produce per-task results and a summary.
Supports direct task files (--task-file) or named benchmark suites (--suite).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from runners.config_loader import load_config
from runners.leaderboard import generate_leaderboard
from runners.result_writer import (
    append_run_raw_result,
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
from runners.benchmark_runner import BenchmarkCancelled, run_benchmark
from runners.resume import completed_attempt_key, load_resume_state


def _build_summary_from_results(
    results: list[dict[str, Any]],
    run_id: str,
    total_tasks: int,
    total_attempts: int,
) -> dict[str, Any]:
    """Build an aggregate summary from completed attempts."""
    completed_attempts = len(results)
    passed = sum(1 for result in results if result["passed"])
    failed = completed_attempts - passed
    return {
        "results": results,
        "run_id": run_id,
        "total_tasks": total_tasks,
        "total_attempts": total_attempts,
        "passed": passed,
        "failed": failed,
        "average_score": (
            sum(result["score"] for result in results) / completed_attempts
            if completed_attempts
            else 0.0
        ),
        "average_latency_sec": (
            sum(result["latency_sec"] for result in results) / completed_attempts
            if completed_attempts
            else 0.0
        ),
    }


def _config_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build the minimum runnable config from resume manifest data."""
    return {
        "id": manifest["model_config_id"],
        "model_name": manifest.get("model_name", ""),
        "runtime": {"server_url": manifest.get("server_url", "")},
        "settings": manifest.get("settings", {}),
    }


def _load_resume_config(manifest: dict[str, Any]) -> dict[str, Any]:
    """Load the original model config if available, otherwise use manifest data."""
    config_id = manifest["model_config_id"]
    config_path = Path("configs") / "models" / f"{config_id}.yaml"
    if config_path.is_file():
        return load_config(str(config_path))
    return _config_from_manifest(manifest)


def _run_resume(args: argparse.Namespace) -> None:
    """Resume an incomplete structured run folder."""
    try:
        state = load_resume_state(args.resume)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error loading resume state: {exc}", file=sys.stderr)
        sys.exit(1)

    status = state.manifest.get("status")
    if status == "completed":
        print(f"Run is already completed: {state.run_dir}", file=sys.stderr)
        sys.exit(1)

    for warning in state.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    try:
        config = _load_resume_config(state.manifest)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading resume config: {exc}", file=sys.stderr)
        sys.exit(1)

    completed_results = [
        result for result in state.completed_results if completed_attempt_key(result)
    ]
    missing_attempts = state.total_attempts - len(state.completed_attempts)
    print(f"Resuming run: {state.run_dir}")
    print(f"Completed attempts found: {len(state.completed_attempts)}/{state.total_attempts}")
    print(f"Missing attempts to run: {missing_attempts}")

    options: dict[str, Any] = {
        "repeats": state.repeats,
        "dry_run": False,
        "task_file": state.manifest["task_file"],
        "run_id": state.manifest["run_id"],
        "run_dir": str(state.run_dir),
        "skip_attempts": state.completed_attempts,
    }
    if state.suite_info:
        options["suite_id"] = state.suite_info["id"]
        options["suite_name"] = state.suite_info["name"]

    new_results: list[dict[str, Any]] = []
    counter_state = [len(state.completed_attempts) + 1]

    def _record_result(result: dict[str, Any]) -> None:
        idx = counter_state[0]
        counter_state[0] += 1
        new_results.append(result)
        append_run_raw_result(state.run_dir, result)
        print(
            f"[{idx}/{state.total_attempts}] {result['task_id']}"
            f" (repeat {result['repeat_index'] + 1}/{state.repeats})  "
            f"score={result['score']}  "
            f"latency={result['latency_sec']:.2f}s"
        )

    try:
        run_benchmark(config, state.tasks, options, result_callback=_record_result)
    except (KeyboardInterrupt, BenchmarkCancelled):
        completed_at = datetime.now().isoformat(timespec="seconds")
        combined_results = completed_results + new_results
        partial_summary = _build_summary_from_results(
            combined_results,
            state.manifest["run_id"],
            len(state.tasks),
            state.total_attempts,
        )
        try:
            write_run_summary(
                state.run_dir,
                partial_summary,
                config,
                state.manifest["task_file"],
                "cancelled",
                repeats=state.repeats,
                suite_info=state.suite_info,
            )
            update_manifest_status(state.run_dir, "cancelled", completed_at)
        except OSError as exc:
            print(f"Error writing cancelled run metadata: {exc}", file=sys.stderr)

        print()
        print("Run cancelled. Completed attempts were preserved.")
        print(f"Run folder: {state.run_dir}")
        sys.exit(130)
    except Exception:
        combined_results = completed_results + new_results
        partial_summary = _build_summary_from_results(
            combined_results,
            state.manifest["run_id"],
            len(state.tasks),
            state.total_attempts,
        )
        try:
            write_run_summary(
                state.run_dir,
                partial_summary,
                config,
                state.manifest["task_file"],
                "failed",
                repeats=state.repeats,
                suite_info=state.suite_info,
            )
            update_manifest_status(
                state.run_dir,
                "failed",
                datetime.now().isoformat(timespec="seconds"),
            )
        except OSError as exc:
            print(f"Error writing failed run metadata: {exc}", file=sys.stderr)
        raise

    combined_results = completed_results + new_results
    summary = _build_summary_from_results(
        combined_results,
        state.manifest["run_id"],
        len(state.tasks),
        state.total_attempts,
    )

    print()
    print(
        f"Total tasks: {summary['total_tasks']} "
        f"(repeats={state.repeats}, total_attempts={summary['total_attempts']})"
    )
    print(f"Passed: {summary['passed']}")
    print(f"Average score: {summary['average_score']:.2f}")
    print(f"Average latency: {summary['average_latency_sec']:.2f}s")

    try:
        write_run_summary(
            state.run_dir,
            summary,
            config,
            state.manifest["task_file"],
            "completed",
            repeats=state.repeats,
            suite_info=state.suite_info,
        )
        update_manifest_status(
            state.run_dir,
            "completed",
            datetime.now().isoformat(timespec="seconds"),
        )
        print(f"Saved raw results to {state.run_dir / 'raw.jsonl'}")
    except OSError as exc:
        print(f"Error writing resumed run metadata: {exc}", file=sys.stderr)

    try:
        write_raw_results(
            combined_results,
            config["id"],
            state.manifest["task_file"],
            state.manifest["run_id"],
        )
    except OSError as exc:
        print(
            f"Error writing raw results compatibility copy: {exc}",
            file=sys.stderr,
        )

    try:
        summary_path = append_summary(
            combined_results,
            config["id"],
            state.manifest["task_file"],
            state.manifest["run_id"],
            repeats=state.repeats,
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
    parser.add_argument("--config", help="Path to YAML config file")
    parser.add_argument("--resume", help="Path to an incomplete structured run folder")

    task_source = parser.add_mutually_exclusive_group()
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

    if args.resume:
        if args.config or args.task_file or args.suite or args.dry_run or args.repeats != 1:
            parser.error("--resume must be used by itself")
        _run_resume(args)
        return

    if not args.config:
        parser.error("--config is required unless --resume is supplied")

    if not args.task_file and not args.suite:
        parser.error("one of --task-file or --suite is required")

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
    completed_results: list[dict[str, Any]] = []

    def _record_result(result: dict[str, Any]) -> None:
        idx = _counter_state[0]
        _counter_state[0] += 1
        completed_results.append(result)
        append_run_raw_result(run_dir, result)
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
    manifest["repeats"] = args.repeats
    manifest["total_tasks"] = len(tasks)
    manifest["total_attempts"] = total_attempts
    write_manifest(run_dir, manifest)

    try:
        summary = run_benchmark(
            config,
            tasks,
            options,
            result_callback=_record_result,
        )
    except (KeyboardInterrupt, BenchmarkCancelled):
        completed_at = datetime.now().isoformat(timespec="seconds")
        partial_summary = _build_summary_from_results(
            completed_results,
            run_id,
            len(tasks),
            total_attempts,
        )
        try:
            write_run_summary(
                run_dir,
                partial_summary,
                config,
                task_file,
                "cancelled",
                repeats=args.repeats,
                suite_info=suite_info,
            )
            update_manifest_status(run_dir, "cancelled", completed_at)
        except OSError as exc:
            print(f"Error writing cancelled run metadata: {exc}", file=sys.stderr)

        print()
        print("Run cancelled. Completed attempts were preserved.")
        print(f"Run folder: {run_dir}")
        print(f"Saved raw results to {run_dir / 'raw.jsonl'}")
        sys.exit(130)
    except Exception:
        partial_summary = _build_summary_from_results(
            completed_results,
            run_id,
            len(tasks),
            total_attempts,
        )
        try:
            write_run_summary(
                run_dir,
                partial_summary,
                config,
                task_file,
                "failed",
                repeats=args.repeats,
                suite_info=suite_info,
            )
        except OSError as exc:
            print(f"Error writing failed run summary: {exc}", file=sys.stderr)
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

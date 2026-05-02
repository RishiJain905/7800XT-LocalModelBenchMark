"""Local Model Benchmark Harness — orchestrates config loading, model prompting,
and scoring across a JSONL task file to produce per-task results and a summary.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
import uuid
from typing import Any

from runners.config_loader import load_config
from runners.llama_client import run_prompt
from runners.leaderboard import generate_leaderboard
from runners.result_writer import append_summary, write_raw_results
from runners.task_loader import load_tasks
from scorers.registry import get_scorer

# ---------------------------------------------------------------------------
# Category → scorer-name mapping
# ---------------------------------------------------------------------------

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


def _resolve_scorer(task: dict[str, Any]) -> str:
    """Return the scorer name for *task* based on its metadata category."""
    category: str = task.get("metadata", {}).get("category", "")
    return CATEGORY_SCORER_MAP.get(category, _FALLBACK_SCORER)


# ---------------------------------------------------------------------------
# Result builders
# ---------------------------------------------------------------------------


def _extract_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Pull the subset of settings fields we track in result records."""
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
    """Construct a result dict for a successfully-executed task."""
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
    }


def _build_error_result(
    task: dict[str, Any],
    config: dict[str, Any],
    error: str,
    task_file: str,
    run_id: str,
) -> dict[str, Any]:
    """Construct a result dict for a task that failed during execution."""
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
    }


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Model Benchmark Harness")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument("--task-file", required=True, help="Path to JSONL task file")
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

    # --- Load configuration ------------------------------------------------
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading config: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Load tasks --------------------------------------------------------
    try:
        tasks = load_tasks(args.task_file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading tasks: {exc}", file=sys.stderr)
        sys.exit(1)

    if not tasks:
        print("No tasks found in task file.", file=sys.stderr)
        sys.exit(1)

    # --- Dry-run: inspect without calling the model ------------------------
    if args.dry_run:
        print(f"Config: {config['id']}")
        print(f"Tasks: {len(tasks)}")
        if args.repeats > 1:
            print(
                f"Repeats: {args.repeats} (total attempts: {len(tasks) * args.repeats})"
            )
        for task in tasks:
            scorer_name = _resolve_scorer(task)
            description = task["description"]
            print(f'  {task["id"]}: "{description}" -> {scorer_name}')
        return

    # --- Normal execution: run every task through the model ----------------
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{uuid.uuid4().hex[:8]}"
    flat_results: list[dict[str, Any]] = []

    for task in tasks:
        scorer_name = _resolve_scorer(task)
        for repeat_idx in range(args.repeats):
            prompt: str = task["description"]

            try:
                model_result = run_prompt(config, prompt)
                scorer = get_scorer(scorer_name)
                score_result = scorer(task, model_result["response"])
                result = _build_result(
                    task, config, model_result, score_result, args.task_file, run_id
                )
            except Exception as exc:
                result = _build_error_result(
                    task, config, str(exc), args.task_file, run_id
                )

            result["repeat_index"] = repeat_idx
            result["repeat_count"] = args.repeats
            flat_results.append(result)

            print(
                f"[{len(flat_results)}/{len(tasks) * args.repeats}] {task['id']} "
                f"(repeat {repeat_idx + 1}/{args.repeats})  "
                f"score={result['score']}  "
                f"latency={result['latency_sec']:.2f}s"
            )

    # --- Summary -----------------------------------------------------------
    total = len(flat_results)
    actual_tasks = len(tasks)
    passed = sum(1 for r in flat_results if r["passed"])
    avg_score = sum(r["score"] for r in flat_results) / total if total else 0.0
    avg_latency = sum(r["latency_sec"] for r in flat_results) / total if total else 0.0

    print()
    print(
        f"Total tasks: {actual_tasks} (repeats={args.repeats}, total_attempts={total})"
    )
    print(f"Passed: {passed}")
    print(f"Average score: {avg_score:.2f}")
    print(f"Average latency: {avg_latency:.2f}s")

    # --- Persist results to disk -------------------------------------------
    try:
        raw_path = write_raw_results(flat_results, config["id"], args.task_file, run_id)
        print(f"Saved raw results to {raw_path}")
    except OSError as exc:
        print(f"Error writing raw results: {exc}", file=sys.stderr)

    try:
        summary_path = append_summary(
            flat_results,
            config["id"],
            args.task_file,
            run_id,
            repeats=args.repeats,
            total_tasks=actual_tasks,
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

# Task 06 — Extract Reusable Runner ✅

## Deliverables

### Created Files

| File | Purpose |
|------|---------|
| `runners/benchmark_runner.py` | Reusable benchmark execution engine — `run_benchmark(config, tasks, options, progress_callback, result_callback) -> dict` |
| `tests/test_benchmark_runner.py` | 27 tests covering normal runs, repeats, dry-run, callbacks, error handling, and internal helpers |

### Modified Files

| File | Changes |
|------|---------|
| `runners/__init__.py` | Exports `run_benchmark` from `benchmark_runner` |
| `run_benchmark.py` | Refactored to thin CLI wrapper — delegates to `runners.benchmark_runner.run_benchmark()` |
| `tests/test_run_benchmark.py` | Updated imports to pull helpers from `runners.benchmark_runner`; updated mock paths from `run_benchmark.run_prompt` → `runners.benchmark_runner.run_prompt` |

## Runner API

```python
def run_benchmark(
    config: dict,
    tasks: list[dict],
    options: dict,
    progress_callback: Callable[[int, int], None] | None = None,
    result_callback: Callable[[dict], None] | None = None,
) -> dict:
```

**Options dict keys:** `repeats`, `dry_run`, `run_id` (auto-generated), `task_file`

**Return dict:** `{ "results": [...], "run_id": str, "total_tasks": int, "total_attempts": int, "passed": int, "failed": int, "average_score": float, "average_latency_sec": float }`

### Support Matrix

| Feature | Status |
|---------|--------|
| Direct config dict and loaded task lists | ✅ |
| Repeats | ✅ |
| Progress callbacks `(completed, total)` | ✅ |
| Result callbacks per-attempt | ✅ |
| Dry-run mode (no model calls) | ✅ |
| Error results when task fails | ✅ |
| TUI can call without shelling out | ✅ (just import and call) |
| Existing CLI output unchanged | ✅ (350 tests pass) |

## Test Coverage

| Category | Tests |
|----------|-------|
| Basic execution (normal + error) | 2 |
| Repeats (3x + error) | 2 |
| Dry-run (no model calls) | 1 |
| Callbacks (progress + result + none) | 3 |
| Internal helpers (resolve_scorer, build_result, build_error, extract_settings) | 9 |
| Import verification | 2 |
| Backward-compatibility CLI tests (main, dry-run, repeats, contract) | 13 |
| Existing Phase 1 tests unchanged | 337 |

## Verification

```powershell
python -m pytest tests/ -q
350 passed in 0.77s

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl --dry-run
# Produces same output as before
```

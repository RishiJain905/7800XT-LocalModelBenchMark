# Task 06 — Main Benchmark Runner: Complete

## Summary

Fully implemented the `run_benchmark.py` CLI entry point and comprehensive test suite.

## Deliverables

### `run_benchmark.py` (192 lines)

The main CLI orchestrator with all required features:

| Feature | Status |
|---|---|
| `--config` (required) — YAML config loading | Done |
| `--task-file` (required) — JSONL task file loading | Done |
| `--dry-run` (optional) — prints what would run without calling model | Done |
| Category-to-scorer mapping (math→numeric_close, text→exact_match, etc.) | Done |
| Per-task execution: prompt → model call → scoring → result | Done |
| Error handling: per-task try/except with score=0.0, continues to next task | Done |
| Progress printing: `[3/10] task_id  score=1.0  latency=1.23s` | Done |
| Summary output: total, passed, avg score, avg latency | Done |
| Result object format with settings metadata | Done |

### `tests/test_run_benchmark.py` (25 tests)

| Test Area | Tests |
|---|---|
| `_resolve_scorer` — category mapping (parametrized) | 12 |
| `_extract_settings` — config settings extraction | 3 |
| `_build_result` — success result object | 1 |
| `_build_error_result` — error result object | 1 |
| CLI argument errors (missing config, missing task-file, file-not-found, empty tasks) | 5 |
| Dry-run output (no model call, correct inspection print) | 1 |
| Full run with mocks (progress, summary, error continuation) | 2 |

## Verification

```
python -m pytest tests/ -v
============================= 236 passed in 0.40s =============================
```

All 236 tests pass — 211 existing (no regressions) + 25 new tests.

## Architecture

```
run_benchmark.py  (CLI entry point)
    |
    ├── runners/config_loader.py   → load_config(path)
    ├── runners/task_loader.py     → load_tasks(path)
    ├── runners/llama_client.py    → run_prompt(config, prompt)
    └── scorers/registry.py        → get_scorer(name)
            ├── scorers/exact_match.py
            ├── scorers/numeric_close.py
            ├── scorers/keyword_match.py
            └── scorers/json_valid.py
```

## Done Criteria Met

- [x] CLI accepts `--config` and `--task-file`
- [x] `--dry-run` works without requiring `llama-server`
- [x] Without `--dry-run`, runs all tasks in a task file
- [x] Scores each response via category-based scorer mapping
- [x] Prints basic summary at end (Total, Passed, Average score, Average latency)

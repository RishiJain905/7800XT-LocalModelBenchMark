# Task 07 — Add Results Storage ✅ DONE

## Status

**Completed** — `runners/result_writer.py` implemented, integrated into `run_benchmark.py`, and verified with 250 passing tests.

## What Was Delivered

### New file: `runners/result_writer.py` (113 lines)

| Function | Writes to | Format |
|---|---|---|
| `write_raw_results(results, model_config_id, task_file, run_id)` | `results/raw/<model_config_id>/<stem>_<run_id>.jsonl` | JSONL — one JSON object per line |
| `append_summary(results, model_config_id, task_file, run_id)` | `results/summary.csv` | CSV — creates header on first write, appends row |

### Updated file: `runners/__init__.py`

Exports `write_raw_results` and `append_summary` alongside existing symbols.

### Updated file: `run_benchmark.py` (+14 lines)

After the summary print block, the benchmark now:
1. Calls `write_raw_results(...)` and prints the saved path
2. Calls `append_summary(...)` and prints the updated path
3. Both calls are wrapped in try/except for `OSError` (disk-full, permissions, etc.)
4. Dry-run mode (`--dry-run`) correctly skips all disk writes (returns early before persistence block)

### Updated file: `tests/test_run_benchmark.py` (+11 tests, 250 total)

| Test Class | Tests | Coverage |
|---|---|---|
| `TestWriteRawResults` | 5 | Directory creation, JSONL writing, stem extraction, empty results, absolute path |
| `TestAppendSummary` | 6 | Header creation, row appending, stats computation (all passed, some failed, empty), float formatting |
| `TestMainFullRun` (augmented) | +3 | Verifies `write_raw_results`/`append_summary` are called, output paths printed, error handling on disk failure |

## Implementation Summary

| Requirement | Implementation |
|---|---|
| Raw JSONL files created per run | `write_raw_results` creates `results/raw/<model_config_id>/<stem>_<run_id>.jsonl` with `mkdir(parents=True)` |
| Summary CSV created if missing | `append_summary` checks `file_exists` and writes header row on first creation |
| New runs append to summary CSV | `open(summary_path, "a")` — always appends a new row |
| Result output paths printed after run | Two `print()` calls show saved raw path and updated summary path |
| Each result includes all required fields | Maps `run_id`, `model_config_id`, `task_id`, `category`, `task_file`, `prompt`, `response`, `latency_sec`, `score`, `passed`, `reason`, `settings` |
| Summary columns | `run_id,model_config_id,task_file,total_tasks,passed,failed,pass_rate,average_score,average_latency_sec` |

## Verification

```
python -m pytest tests/ -v
============================= 250 passed in 0.47s =============================
```

All 250 tests pass — 239 existing (no regressions) + 11 new tests.

## Done Criteria Met

- [x] Raw JSONL files are created for each run in `results/raw/<model_config_id>/`
- [x] `summary.csv` is created if it does not exist
- [x] New benchmark runs append a new row to `summary.csv`
- [x] Result output paths are printed after each run
- [x] Dry-run mode skips all disk writes
- [x] Disk write errors are caught and reported without crashing

## Architecture

```
run_benchmark.py  (CLI entry point — now calls result_writer after summary)
    |
    ├── runners/config_loader.py    → load_config(path)
    ├── runners/task_loader.py      → load_tasks(path)
    ├── runners/llama_client.py     → run_prompt(config, prompt)
    ├── runners/result_writer.py    → write_raw_results(), append_summary()  ★ NEW
    └── scorers/registry.py         → get_scorer(name)
```

Expected output structure after a run:

```
results/
├─ raw/
│  └─ <model_config_id>/
│     └─ <stem>_<run_id>.jsonl
├─ summary.csv
└─ reports/
```

## Notes

- Uses only stdlib modules: `json`, `csv`, `pathlib`, `statistics`
- No new dependencies added
- Style consistent with existing codebase (PEP 8, type hints, docstrings, `from __future__ import annotations`)
- Float formatting: `pass_rate`/`average_score` at `:.4f`, `average_latency_sec` at `:.3f`

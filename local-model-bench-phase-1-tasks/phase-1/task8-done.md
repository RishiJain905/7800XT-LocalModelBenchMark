# Task 08 — Generate Markdown Leaderboard ✅ DONE

## Status

**Completed** — `runners/leaderboard.py` implemented, integrated into `run_benchmark.py` and `runners/__init__.py`, and verified with 259 passing tests (no regressions).

## What Was Delivered

### New file: `runners/leaderboard.py` (137 lines)

| Function | Signature | Reads | Writes |
|---|---|---|---|
| `generate_leaderboard(summary_csv_path, output_path)` | `(str, str) -> str` | `results/summary.csv` | `results/reports/leaderboard.md` |

Key behaviors:
- **Deduplication**: Groups rows by `(model_config_id, task_file)`, keeps only the most recent `run_id` per pair
- **Sorting**: `average_score` desc → `pass_rate` desc → `average_latency_sec` asc
- **Formatting**: Pass Rate as `XX.X%`, Avg Score as `X.XX`, Avg Latency as `X.XXs`
- **Edge cases**: Missing CSV → writes "No data yet." + warning to stderr; empty CSV → same; I/O errors → caught and reported
- **Returns**: Absolute path of the written leaderboard file

### Updated file: `runners/__init__.py` (+2 lines)

Now imports and exports `generate_leaderboard` alongside existing symbols.

### Updated file: `run_benchmark.py` (+6 lines)

After the `append_summary()` persistence block, `run_benchmark.py` now calls `generate_leaderboard()` wrapped in a try/except `OSError` block, printing the leaderboard path on success.

### New file: `results/reports/leaderboard.md` (generated)

Example output:
```markdown
# Local Model Benchmark Leaderboard

| Model Config | Task File | Total Tasks | Pass Rate | Avg Score | Avg Latency |
|---|---:|---:|---:|---:|---:|
| full-cfg | tasks/math/basic_math.jsonl | 10 | 100.0% | 1.00 | 0.50s |
| err-cfg | tasks/math/basic_math.jsonl | 10 | 50.0% | 0.50 | 0.12s |
```

### New file: `tests/test_leaderboard.py` (6 tests)

| Test | Coverage |
|---|---|
| `test_creates_leaderboard_from_summary_csv` | Happy path: CSV → Markdown with correct header, separator, row order, and formatting |
| `test_sorting_by_score_then_pass_rate_then_latency` | Multi-key sort verification |
| `test_deduplication_keeps_most_recent_run` | Same `(model_config_id, task_file)` pair keeps latest run |
| `test_empty_csv` | Header-only CSV produces "No data yet." leaderboard |
| `test_missing_csv_file` | Non-existent CSV writes "No data yet." and prints warning to stderr |
| `test_returns_absolute_path` | Return value is an absolute path string |

### Updated file: `tests/test_run_benchmark.py` (+3 integration tests)

| Test | Coverage |
|---|---|
| `test_generate_leaderboard_is_called` | `generate_leaderboard()` is invoked once during a normal run |
| `test_leaderboard_path_is_printed` | `"Updated leaderboard at"` appears in stdout |
| `test_generate_leaderboard_error_handling` | `OSError` is caught and `"Error writing leaderboard"` printed to stderr |

## Implementation Summary

| Requirement | Implementation |
|---|---|
| `runners/leaderboard.py` exists | 137-line module with `generate_leaderboard()` public API |
| `results/reports/leaderboard.md` is created | Written to `results/reports/` with `mkdir(parents=True)` |
| Leaderboard updates after every run | Called at end of `main()` after `append_summary()` |
| Sorted by avg_score / pass_rate / latency | `parsed.sort(key=lambda r: (-avg_score, -pass_rate, +latency))` |
| Deduplicates by latest run | Groups by `(model_config_id, task_file)`, picks `max(run_id)` |
| CSV missing/empty handled gracefully | Writes "No data yet." + warning to stderr |

## Verification

```
python -m pytest tests/ -v
============================= 259 passed in 0.52s =============================
```

All 259 tests pass — 250 existing (no regressions) + 9 new tests (6 unit + 3 integration).

## Done Criteria Met

- [x] `runners/leaderboard.py` exists
- [x] `results/reports/leaderboard.md` is created
- [x] The leaderboard updates after every run
- [x] The leaderboard is sorted by score/pass rate/latency

## Architecture

```
run_benchmark.py  (CLI entry point — now calls generate_leaderboard after summary)
    |
    ├── runners/config_loader.py   → load_config(path)
    ├── runners/task_loader.py     → load_tasks(path)
    ├── runners/llama_client.py    → run_prompt(config, prompt)
    ├── runners/leaderboard.py     → generate_leaderboard()              ★ NEW
    ├── runners/result_writer.py   → write_raw_results(), append_summary()
    └── scorers/registry.py        → get_scorer(name)
```

Expected output structure after a run:

```
results/
├─ raw/
│  └─ <model_config_id>/
│     └─ <stem>_<run_id>.jsonl
├─ summary.csv
└─ reports/
   └─ leaderboard.md               ★ NEW
```

## Notes

- Uses only stdlib modules: `csv`, `pathlib`, `collections`, `sys`
- No new dependencies added
- Style consistent with existing codebase (PEP 8, type hints, docstrings, `from __future__ import annotations`)
- Float formatting: pass rate as `:.1f%`, avg score as `:.2f`, avg latency as `:.2fs`

# Task 09 — Repeat-Run Support — Done

## Summary

Added `--repeats` CLI argument to run each benchmark task multiple times, reducing noise and measuring response consistency.

## Files Modified

| File | Change |
|------|--------|
| `run_benchmark.py` | Added `--repeats` CLI arg (int, default=1); wrapped per-task execution in repeat loop; injects `repeat_index` and `repeat_count` into each result; summary shows total tasks vs total attempts; passes `repeats` and `total_tasks` to `append_summary()` |
| `runners/result_writer.py` | `append_summary()` accepts new `repeats` and `total_tasks` parameters; CSV now includes `total_attempts` and `repeats` columns |
| `runners/leaderboard.py` | Leaderboard parses `total_attempts` and `repeats` from CSV (with backward-compatible fallbacks); renders new columns in Markdown table |
| `tests/test_run_benchmark.py` | Updated existing tests for new CSV column layout and stdout format; added `TestMainRepeats` class (3 tests) covering defaults, repeats=3, and error handling during repeats |
| `tests/test_leaderboard.py` | Updated CSV fixtures and assertions for new columns; added `test_old_format_csv_still_works` backward-compat test |

## Done Criteria Verification

- [x] `--repeats` exists and is an integer argument
- [x] Default repeat count is 1 (backward compatible)
- [x] Repeat count > 1 runs each task multiple times
- [x] Raw results include `repeat_index` and `repeat_count` metadata
- [x] Summary CSV correctly counts `total_tasks`, `total_attempts`, and `repeats`
- [x] Leaderboard still works with repeated runs (including old-format CSVs)
- [x] All 264 tests pass

## Test Results

```
python -m pytest tests/ -v
============================= 264 passed in 0.54s ==============================
```

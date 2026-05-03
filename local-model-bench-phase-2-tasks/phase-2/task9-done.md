# Task 09 Done - Interrupt-Safe Runs

## Implemented

- Added durable per-attempt streaming with `append_run_raw_result()` in `runners/result_writer.py`.
- Each completed attempt is appended to structured `raw.jsonl`, flushed, and fsynced immediately.
- Added `BenchmarkCancelled` and runner-level `cancel_callback` support in `runners/benchmark_runner.py`.
- Preserved ordinary model-call exception behavior as failed attempt rows.
- Updated `run_benchmark.py` so Ctrl+C writes a partial summary, marks the manifest `cancelled`, preserves completed raw results, and exits with code `130`.
- Updated unexpected top-level failure handling to write a partial failed summary when possible.
- Kept completed-run compatibility outputs for `results/raw/`, `results/summary.csv`, and the leaderboard.

## Tests Added

- Streaming JSONL append writes one readable JSON object per completed attempt.
- Multiple appends preserve valid JSONL.
- Streaming writer calls `flush()` and `os.fsync()`.
- Runner cancellation stops before the next model call.
- Ctrl+C preserves completed attempts, marks the manifest `cancelled`, and writes a partial `summary.json`.
- Cancelled runs do not write compatibility summary or leaderboard rows.

## Verification

```powershell
python -m pytest tests/test_result_writer.py tests/test_benchmark_runner.py tests/test_run_benchmark.py -q
```

Result: `93 passed`

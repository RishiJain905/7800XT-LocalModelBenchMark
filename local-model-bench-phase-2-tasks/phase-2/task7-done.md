# Task 07 Done - Structured Run Storage

## Implemented

- Added structured run storage helpers in `runners/result_writer.py`.
- Added per-run folders under `results/runs/<model_id>/<run_id>/`.
- Added run `manifest.json`, `raw.jsonl`, `summary.json`, and `artifacts/` creation.
- Added manifest status updates for `running`, `completed`, `cancelled`, and `failed`.
- Updated `run_benchmark.py` to create the structured run folder and write the manifest before model calls begin.
- Updated successful runs to write structured raw results and per-run summary data.
- Kept existing `results/summary.csv` and `results/reports/leaderboard.md` updates intact.
- Kept the old flat raw writer available as a compatibility copy.
- Preserved dry-run behavior without creating run folders.

## Tests Added

- Structured run folder creation.
- Manifest writing and status updates.
- Invalid status rejection.
- Structured `raw.jsonl` and `summary.json` writing.
- CLI structured run file creation.
- Dry-run no-op storage behavior.
- Top-level run failure marking the manifest as `failed`.

## Verification

```powershell
python -m pytest tests/ -q
```

Result: `357 passed`

```powershell
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --dry-run
```

Result: passed and printed the expected dry-run task inspection.

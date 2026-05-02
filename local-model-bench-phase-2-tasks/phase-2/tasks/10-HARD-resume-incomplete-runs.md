# [HARD] Task 10 - Resume Incomplete Runs

## Goal

Allow interrupted or failed runs to continue without rerunning completed attempts.

## Required behavior

Support resume by run folder:

```powershell
python run_benchmark.py --resume results/runs/qwen-9b-q8-4k/2026-05-02_14-30-00
```

The TUI should also list resumable runs.

## Resume logic

- Read `manifest.json`.
- Read existing `raw.jsonl`.
- Identify completed `(task_id, repeat_index)` attempts.
- Continue only missing attempts.
- Append new results to the same `raw.jsonl`.
- Update summary and manifest when complete.

## Done criteria

- Resume works from the batch CLI.
- Resume works from the TUI.
- Already completed attempts are not repeated.
- Tests cover partial raw files, completed runs, and corrupted/incomplete lines.


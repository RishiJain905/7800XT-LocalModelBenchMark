# [HARD] Task 07 - Structured Run Storage

## Goal

Replace the flat raw-output-only storage model with structured per-model run folders while preserving summary and leaderboard compatibility.

## Required output structure

For every run, create:

```text
results/runs/<model_id>/<run_id>/
  manifest.json
  raw.jsonl
  summary.json
  artifacts/
```

## Manifest fields

`manifest.json` should include:

```json
{
  "run_id": "2026-05-02_14-30-00",
  "model_config_id": "qwen-9b-q8-4k",
  "model_name": "Qwen3.5-9B",
  "suite_id": "reasoning.math",
  "task_file": "benchmarks/reasoning/math.jsonl",
  "server_url": "http://127.0.0.1:8080/v1/chat/completions",
  "settings": {},
  "status": "running",
  "started_at": "...",
  "completed_at": null
}
```

## Required behavior

- Create the run folder before model calls begin.
- Write the manifest before the first task runs.
- Update run status as `running`, `completed`, `cancelled`, or `failed`.
- Keep writing `results/summary.csv`.
- Keep generating `results/reports/leaderboard.md`.

## Done criteria

- Every run has a complete folder.
- Existing summary and leaderboard still update.
- Tests cover manifest creation and status updates.
- Paths are stable and Windows-friendly.


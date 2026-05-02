# Task 16 - Improve Summary and Leaderboard

## Goal

Update summaries and leaderboards to understand suites, run folders, and model-level comparison.

## Required outputs

Continue writing:

```text
results/summary.csv
results/reports/leaderboard.md
```

Also create per-run:

```text
results/runs/<model_id>/<run_id>/summary.json
```

## Required fields

Add summary fields for:

- `suite_id`
- `suite_name`
- `run_folder`
- `status`
- `started_at`
- `completed_at`
- `artifact_count`

## Leaderboard behavior

Leaderboard should support ranking by:

1. Average score.
2. Pass rate.
3. Average latency.

It should group meaningfully by suite so coding runs do not hide math runs.

## Done criteria

- Old summary fields remain available.
- New summary fields are populated.
- Leaderboard includes suite information.
- Tests cover sorting and deduping latest run per model/suite.


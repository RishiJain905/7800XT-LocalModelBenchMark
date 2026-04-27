# Task 08 — Generate Markdown Leaderboard

## Goal

Generate a simple Markdown leaderboard from `results/summary.csv`.

The leaderboard should make it easy to compare model configs across task files.

## Required file

Create:

```text
runners/leaderboard.py
```

Expose:

```python
def generate_leaderboard(summary_csv_path: str = "results/summary.csv", output_path: str = "results/reports/leaderboard.md") -> str:
    ...
```

## Required output

Create or update:

```text
results/reports/leaderboard.md
```

Example content:

```markdown
# Local Model Benchmark Leaderboard

| Model Config | Task File | Total Tasks | Pass Rate | Avg Score | Avg Latency |
|---|---:|---:|---:|---:|---:|
| qwen-9b-q8-4k | tasks/math/basic_math.jsonl | 10 | 90.0% | 0.90 | 1.42s |
| qwen-18b-iq4-4k | tasks/math/basic_math.jsonl | 10 | 95.0% | 0.95 | 2.88s |
```

## Sorting

Sort rows by:

1. Highest average score
2. Highest pass rate
3. Lowest average latency

## Required runner integration

Update `run_benchmark.py` so that after writing raw results and summary CSV, it also regenerates the leaderboard.

Example terminal output:

```text
Updated leaderboard at results/reports/leaderboard.md
```

## Done criteria

This task is done when:

- `runners/leaderboard.py` exists.
- `results/reports/leaderboard.md` is created.
- The leaderboard updates after every run.
- The leaderboard is sorted by score/pass rate/latency.

# Task 07 — Add Results Storage

## Goal

Save every benchmark run to disk in a clean and organized way.

Raw outputs are important. Do not only save scores.

## Required output structure

The benchmark should write to:

```text
results/
├─ raw/
│  └─ <model_config_id>/
│     └─ <task_file_name>_<run_id>.jsonl
│
├─ summary.csv
│
└─ reports/
```

Example:

```text
results/raw/qwen-9b-q8-4k/basic_math_2026-04-27_03-15-42.jsonl
results/summary.csv
```

## Required implementation

Create:

```text
runners/result_writer.py
```

Expose:

```python
def write_raw_results(results: list[dict], model_config_id: str, task_file: str, run_id: str) -> str:
    ...


def append_summary(results: list[dict], model_config_id: str, task_file: str, run_id: str) -> str:
    ...
```

## Raw results

Write one JSON object per line.

Each result should include:

- `run_id`
- `model_config_id`
- `task_id`
- `category`
- `task_file`
- `prompt`
- `response`
- `latency_sec`
- `score`
- `passed`
- `reason`
- model/runtime settings if available

## Summary CSV

Create or update:

```text
results/summary.csv
```

Columns:

```csv
run_id,model_config_id,task_file,total_tasks,passed,failed,pass_rate,average_score,average_latency_sec
```

## Required runner integration

Update `run_benchmark.py` so that after a benchmark run:

1. Raw results are written.
2. Summary CSV is appended.
3. Output paths are printed.

Example terminal output:

```text
Saved raw results to results/raw/qwen-9b-q8-4k/basic_math_2026-04-27_03-15-42.jsonl
Updated summary at results/summary.csv
```

## Done criteria

This task is done when:

- Raw JSONL files are created for each run.
- `summary.csv` is created if it does not exist.
- New benchmark runs append a new row to `summary.csv`.
- Result output paths are printed after each run.

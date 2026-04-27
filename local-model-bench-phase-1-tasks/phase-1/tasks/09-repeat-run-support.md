# Task 09 — Add Repeat-Run Support

## Goal

Support running each task multiple times to reduce noise and measure response consistency.

Even with deterministic settings, local model output and runtime speed can vary. Repeat runs help compare models more fairly.

## Required CLI argument

Add:

```text
--repeats
```

Example:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl --repeats 3
```

Default:

```text
--repeats 1
```

## Required behavior

If `--repeats 3` is passed:

- Each task is run 3 times.
- Each raw result line should include:
  - `repeat_index`
  - `repeat_count`

Example:

```json
{
  "task_id": "math_001",
  "repeat_index": 1,
  "repeat_count": 3,
  "score": 1.0,
  "passed": true
}
```

## Summary behavior

The summary should aggregate over all task attempts.

Example:

- 10 tasks
- 3 repeats
- 30 total attempts

The summary CSV can use:

```csv
total_tasks,total_attempts,passed,failed,pass_rate,average_score,average_latency_sec
```

Update `summary.csv` columns if needed to include `total_attempts`.

Recommended final columns:

```csv
run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,pass_rate,average_score,average_latency_sec,repeats
```

## Optional consistency metric

Add a simple response variation metric if easy:

```text
unique_responses_per_task
```

This is optional for Phase 1.

## Done criteria

This task is done when:

- `--repeats` exists.
- Default repeat count is 1.
- Repeat count greater than 1 runs each task multiple times.
- Raw results include repeat metadata.
- Summary CSV correctly counts total attempts.
- Leaderboard still works with repeated runs.

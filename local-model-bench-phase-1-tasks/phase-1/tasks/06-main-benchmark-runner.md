# Task 06 — Build Main Benchmark Runner

## Goal

Implement the main CLI command that loads a model config, loads a task file, runs each task against the local model, scores responses, and returns structured results.

## Required file

Update:

```text
run_benchmark.py
```

## Required CLI

Support this command:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl
```

Required arguments:

```text
--config
--task-file
```

Optional argument for now:

```text
--dry-run
```

`--dry-run` should load config and tasks, print what would run, but not call the model.

## Required behavior

The runner should:

1. Load the config using `runners.config_loader.load_config`.
2. Load tasks using `runners.task_loader.load_tasks`.
3. For each task:
   - Send the prompt to the model using `runners.llama_client.run_prompt`.
   - Score the response using the scorer from `scorers.registry.get_scorer`.
   - Build a result object.
4. Print progress to the terminal.

## Result object format

For each task, produce:

```json
{
  "run_id": "2026-04-27_001",
  "model_config_id": "qwen-9b-q8-4k",
  "task_id": "math_001",
  "category": "math",
  "task_file": "tasks/math/basic_math.jsonl",
  "prompt": "What is 17% of 850? Give only the number.",
  "expected": "144.5",
  "response": "144.5",
  "latency_sec": 1.21,
  "score": 1.0,
  "passed": true,
  "reason": "Matched expected answer"
}
```

Include config/runtime metadata if possible:

```json
{
  "settings": {
    "context_size": 4096,
    "temperature": 0,
    "top_p": 1,
    "max_tokens": 1024
  }
}
```

## Run ID

Generate a run ID using the current date/time.

Example:

```text
2026-04-27_03-15-42
```

## Done criteria

This task is done when:

- The CLI accepts `--config` and `--task-file`.
- `--dry-run` works without requiring `llama-server` to be running.
- Without `--dry-run`, it runs all tasks in a task file.
- It scores each response.
- It prints a basic summary at the end:

```text
Total tasks: 10
Passed: 8
Average score: 0.82
Average latency: 1.45s
```

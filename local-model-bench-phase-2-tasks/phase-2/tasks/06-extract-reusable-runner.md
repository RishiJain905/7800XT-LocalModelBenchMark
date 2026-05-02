# Task 06 - Extract Reusable Runner

## Goal

Move benchmark execution logic out of `run_benchmark.py` so both the batch CLI and terminal UI can use the same core runner.

## Required file

Create:

```text
runners/benchmark_runner.py
```

## Required API

Expose a simple function or class such as:

```python
def run_benchmark(config: dict, tasks: list[dict], options: dict) -> dict:
    ...
```

It should support:

- Repeats.
- Progress callbacks.
- Result callbacks after each attempt.
- Dry-run mode.
- Error results when a task fails.

## Required integration

Update:

```text
run_benchmark.py
```

The CLI should become a thin wrapper around the reusable runner.

## Done criteria

- Existing CLI output remains substantially the same.
- TUI can call the runner without shelling out.
- Tests cover the reusable runner directly.
- Existing Phase 1 tests still pass.


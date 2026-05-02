# Task 03 - Create Benchmark Suite Registry

## Goal

Add a registry that discovers and describes available benchmark suites.

## Required files

Create:

```text
runners/suite_registry.py
benchmarks/suites.yaml
```

## Required behavior

The registry should expose:

```python
def list_suites() -> list[dict]:
    ...

def get_suite(suite_id: str) -> dict:
    ...
```

Each suite should include:

```yaml
id: reasoning.math
name: Math
category: reasoning
task_file: benchmarks/reasoning/math.jsonl
description: Numeric and short-answer math prompts.
scoring: deterministic
```

## Done criteria

- Suites can be listed without loading tasks.
- Missing task files produce clear validation errors.
- The batch runner can use a suite ID in addition to a raw task file path.
- Tests cover suite listing, lookup, and missing-suite errors.


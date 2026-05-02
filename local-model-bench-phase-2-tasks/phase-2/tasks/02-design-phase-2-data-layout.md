# Task 02 - Design Phase 2 Data Layout

## Goal

Define the folder and file layout for benchmark suites, model configs, and run results.

## Required structure

Introduce this target structure:

```text
benchmarks/
  coding/
    frontend.jsonl
    backend.jsonl
    misc.jsonl
  reasoning/
    math.jsonl
    real_world.jsonl
    instruction_following.jsonl
  tools/
    json_tool_calling.jsonl
  context/
    long_context.jsonl
  official/
    README.md

configs/
  models/
    qwen-9b-q8-4k.yaml

results/
  runs/
    <model_id>/
      <run_id>/
        manifest.json
        raw.jsonl
        summary.json
        artifacts/
```

## Required documentation

Update or create:

```text
docs/results_layout.md
docs/benchmark_suite_format.md
```

## Done criteria

- The target layout is documented.
- Naming rules for `model_id`, `suite_id`, and `run_id` are explicit.
- The layout supports multiple models and multiple runs per model.
- The layout is Windows-friendly.


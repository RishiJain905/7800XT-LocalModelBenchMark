# Local Model Benchmark Harness — Agent Task Pack

This task pack is for creating **Phase 1** of a local model benchmarking harness.

The goal is to build a lightweight, reproducible benchmark system for comparing local LLMs and different runtime settings, especially models served through `llama.cpp` / `llama-server`.

This is intentionally designed so a coding agent can complete the project sequentially.

## How to use this pack

Give the entire folder to your coding agent and tell it:

> Read `phase-1/README.md` first. Then complete the task files in order from Task 01 to Task 10. Do not skip ahead. After each task, update the implementation and confirm the done criteria.

## Phase 1 goal

By the end of Phase 1, the repo should support commands like:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl
```

And produce:

```text
results/raw/<model_config_id>/<task_file>_<run_id>.jsonl
results/summary.csv
results/reports/leaderboard.md
```

## Phase 1 scope

Phase 1 includes:

- Local benchmark repo structure
- YAML model configs
- JSONL task files
- `llama-server` API client
- Basic scorers
- Main benchmark runner
- Raw result storage
- Summary CSV
- Markdown leaderboard
- Repeat-run support
- README usage documentation

Phase 1 does **not** include full Hermes Agent integration yet. That comes later.

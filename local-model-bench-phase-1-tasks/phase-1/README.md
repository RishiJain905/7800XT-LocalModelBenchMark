# Phase 1 — Core Local Model Benchmark Harness

## Objective

Build the minimum useful benchmark harness for local LLMs.

The harness should run the same tasks against different local model configurations through an OpenAI-compatible `llama-server` endpoint, score the results, and save clean outputs.

## Completion criteria

Phase 1 is complete when all ten tasks are done and this command works:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl
```

Expected outputs:

```text
results/raw/qwen-9b-q8-4k/math_basic_math_<run_id>.jsonl
results/summary.csv
results/reports/leaderboard.md
```

## Sequential task list

Complete these in order:

1. `tasks/01-create-repo-structure.md`
2. `tasks/02-model-config-format.md`
3. `tasks/03-task-file-format.md`
4. `tasks/04-llama-server-api-client.md`
5. `tasks/05-basic-scorers.md`
6. `tasks/06-main-benchmark-runner.md`
7. `tasks/07-results-storage.md`
8. `tasks/08-leaderboard-generation.md`
9. `tasks/09-repeat-run-support.md`
10. `tasks/10-readme-usage-docs.md`

## Important implementation principles

- Keep Phase 1 lightweight.
- Prefer simple Python files over complex frameworks.
- Use deterministic settings by default: temperature `0`, top_p `1`.
- Every result must include the model config ID and runtime settings.
- Avoid hardcoding one model. The whole point is comparing many configs.
- Store raw outputs. Do not only store scores.
- The benchmark should be usable on Windows.
- Assume the user may run this with `llama.cpp` compiled for ROCm on an AMD GPU.

## Suggested tech stack

- Python 3.10+
- `requests`
- `PyYAML`
- Standard library modules: `json`, `csv`, `time`, `datetime`, `pathlib`, `argparse`, `statistics`


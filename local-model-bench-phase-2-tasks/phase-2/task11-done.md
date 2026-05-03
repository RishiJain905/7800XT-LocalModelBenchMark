# Task 11 Done - Core Benchmark Suites

Implemented the required non-coding benchmark suites for local model comparison.

## Completed

- Expanded `benchmarks/reasoning/math.jsonl` to 20 deterministic math tasks.
- Expanded `benchmarks/reasoning/real_world.jsonl` to 20 constrained real-world reasoning tasks.
- Expanded `benchmarks/reasoning/instruction_following.jsonl` to 20 constrained instruction-following tasks.
- Kept existing suite IDs and registry shape unchanged in `benchmarks/suites.yaml`.
- Added acceptance coverage that verifies the three Task 11 reasoning suites are registered, load as JSONL, and contain 20 tasks each.
- Preserved the existing public CLI interface and scorer selection behavior.

## Verification

```powershell
python -m pytest tests/test_task_loader.py tests/test_suite_registry.py -q
```

Result: `51 passed`

```powershell
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --dry-run
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.real_world --dry-run
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.instruction_following --dry-run
```

Result: each dry-run resolved the suite successfully and printed `Tasks: 20`.

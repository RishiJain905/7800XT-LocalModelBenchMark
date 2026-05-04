# Task 14 - Add Long-Context Suite Done

Completed: 2026-05-03

## Summary

- Populated `benchmarks/context/long_context.jsonl` with 8 deterministic long-context tasks.
- Covered early fact recall, buried instruction retention, required-keyword summarization, and cross-section comparison.
- Kept the existing `context.long_context` registration in `benchmarks/suites.yaml`.
- Added raw result metadata preservation via `task_metadata` and `prompt_size_chars`.
- Added acceptance coverage for long-context task count, metadata, prompt size, scorer categories, and task type coverage.

## Confirmations

- The suite loads through `run_benchmark.py --suite context.long_context --dry-run`.
- Each task records `metadata.suite_category`, `metadata.task_type`, `metadata.estimated_context_tokens`, and `metadata.prompt_size_chars`.
- Summary tasks use deterministic `keyword_match` scoring through `metadata.category: "keyword"`.
- Recall, buried-instruction, and comparison tasks use deterministic `exact_match` scoring through `metadata.category: "text"`.
- Existing Task 13 completion note was left untouched.

## Verification

```powershell
python -m pytest tests/test_benchmark_runner.py tests/test_suite_registry.py tests/test_task_loader.py -q
# 85 passed in 0.45s

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite context.long_context --dry-run
# Config: qwen-9b-q8-4k
# Tasks: 8
# Suite: context.long_context (Long Context)

python -m pytest tests/ -q
# 384 passed in 1.21s
```

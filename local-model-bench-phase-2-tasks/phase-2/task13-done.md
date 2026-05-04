# Task 13 - Add Tool Calling Suite Done

Completed: 2026-05-03

## Summary

- Populated `benchmarks/tools/json_tool_calling.jsonl` with 20 strict JSON tool-calling tasks.
- Covered weather lookup, calculator, file search, calendar event creation, email drafting, data extraction, and multi-argument tool calls.
- Kept the existing `tools.json_tool_calling` suite registration in `benchmarks/suites.yaml`.
- Updated `json_valid` scoring so valid JSON objects, expected tool matches, and each required argument key receive independent scoring credit.

## Confirmations

- Invalid JSON returns a clear `Invalid JSON:` failure reason.
- Partial tool-call correctness receives partial credit at the argument-key level.
- Tool-call expectations continue to work from either top-level task fields or `metadata`.
- Dry-run and normal runner scoring paths are covered by tests.

## Verification

```powershell
python -m pytest tests/test_scorers.py tests/test_suite_registry.py tests/test_benchmark_runner.py -q
# 144 passed in 0.36s

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite tools.json_tool_calling --dry-run
# Loaded 20 tasks for tools.json_tool_calling using json_valid.

python -m pytest tests/ -q
# 383 passed in 1.27s
```

# Task 03 — Create Benchmark Suite Registry ✅

## Deliverables

### Created Files

| File | Purpose |
|------|---------|
| `benchmarks/suites.yaml` | YAML registry with 8 initial suites (reasoning.math, reasoning.real_world, reasoning.instruction_following, coding.frontend, coding.backend, coding.misc, tools.json_tool_calling, context.long_context) |
| `benchmarks/reasoning/math.jsonl` | Stub JSONL for math suite |
| `benchmarks/reasoning/real_world.jsonl` | Stub JSONL for real-world reasoning |
| `benchmarks/reasoning/instruction_following.jsonl` | Stub JSONL for instruction following |
| `benchmarks/coding/frontend.jsonl` | Stub JSONL for frontend coding |
| `benchmarks/coding/backend.jsonl` | Stub JSONL for backend coding |
| `benchmarks/coding/misc.jsonl` | Stub JSONL for misc coding |
| `benchmarks/tools/json_tool_calling.jsonl` | Stub JSONL for tool calling |
| `benchmarks/context/long_context.jsonl` | Stub JSONL for long context |
| `runners/suite_registry.py` | Suite registry module with `list_suites()` and `get_suite()` |
| `tests/test_suite_registry.py` | 16 tests covering listing, lookup, validation, and integration |

### Modified Files

| File | Changes |
|------|---------|
| `runners/__init__.py` | Exports `list_suites`, `get_suite`, `clear_cache` |
| `run_benchmark.py` | Added `--suite` CLI arg as mutually exclusive alternative to `--task-file` |

### Done Criteria

| Criteria | Status |
|----------|--------|
| Suites can be listed without loading tasks | ✅ `list_suites()` returns metadata only |
| Missing task files produce clear validation errors | ✅ `ValueError` with exact file path |
| Batch runner can use a suite ID (`--suite`) | ✅ `--suite` resolves task_file path via registry |
| Existing `--task-file` still works | ✅ Mutual exclusive group enforces one or the other |
| Tests cover suite listing, lookup, and missing-suite errors | ✅ 16 tests, 290 total passing |

## Verification

```
python -m pytest tests/ -q
290 passed in 0.66s

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite reasoning.math --dry-run
Config: qwen-9b-q8-4k
Tasks: 1
Suite: reasoning.math (Math)
  math_add: "What is 2+2?" -> numeric_close

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file benchmarks/reasoning/math.jsonl --dry-run
Config: qwen-9b-q8-4k
Tasks: 1
  math_add: "What is 2+2?" -> numeric_close
```

# Task 04 — Create Model Registry ✅

## Deliverables

### Created Files

| File | Purpose |
|------|---------|
| `runners/model_registry.py` | Model registry module with `list_model_configs()`, `get_model_config()`, `clear_cache()` |
| `configs/models/qwen-9b-q8-4k.yaml` | Copy of existing config into the models subdirectory |
| `tests/test_model_registry.py` | 13 tests covering listing, lookup, validation errors, and backward compatibility |

### Modified Files

| File | Changes |
|------|---------|
| `runners/__init__.py` | Exports `list_model_configs`, `get_model_config` from model registry |
| `run_benchmark.py` | Added `import os`, `_resolve_config_path()` helper that accepts direct paths (backward compat) or model IDs; config loading now uses it |

### Done Criteria

| Criteria | Status |
|----------|--------|
| Multiple model configs can exist under `configs/models/` | ✅ Filesystem scan of `*.yaml` files |
| The app can list model IDs and human-readable model names | ✅ `list_model_configs()` returns all configs with `id` and `model_name` |
| Direct path configs still work | ✅ `_resolve_config_path()` checks `os.path.isfile()` first |
| Tests cover listing, lookup, duplicate IDs, and invalid configs | ✅ 13 tests covering all cases |

## Verification

```
python -m pytest tests/ -q
303 passed in 0.68s

python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --dry-run
Config: qwen-9b-q8-4k
Tasks: 1
Suite: reasoning.math (Math)
  math_add: "What is 2+2?" -> numeric_close

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl --dry-run
Config: qwen-9b-q8-4k
Tasks: 4
  math_add: ...
  text_capital_france: ...
  keyword_transformer: ...
  json_weather_tool: ...
```

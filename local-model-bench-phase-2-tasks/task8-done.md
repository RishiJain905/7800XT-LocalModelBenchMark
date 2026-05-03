# Task 08 - Save Coding Artifacts — Complete

## Goal

Save model-generated coding outputs as standalone files so frontend/backend/misc coding benchmark responses are easy to inspect.

## Changes Made

### `runners/result_writer.py` — Two new functions

- **`sanitize_filename(name: str) -> str`** — Sanitizes task IDs for use in filenames. Replaces any non-alphanumeric character (except `-`, `_`, `.`) with `_` using `re.sub()`.

- **`save_artifact(run_dir, suite_id, task, response) -> str`** — Saves a model response to:
  ```
  <run_dir>/artifacts/<suite_id>/<sanitized_task_id>_response.<ext>
  ```
  - Extension from `task.metadata.artifact_extension` (default: `.md`)
  - Creates suite subdirectory as needed
  - Returns absolute path string
  - No existing functions modified.

### `runners/benchmark_runner.py` — Integration in run loop

- **`_build_result()`**: Added `"artifact_paths": []` to result dict
- **`_build_error_result()`**: Added `"artifact_paths": []` to error result dict
- **`run_benchmark()`**: After each attempt, if `category == "code"` and `options` contains `"run_dir"`, calls `save_artifact()` and appends the path to `result["artifact_paths"]`

### `run_benchmark.py` — Passes run_dir to options

- Added `options["run_dir"] = str(run_dir)` right after `create_run_folder()`, before `run_benchmark()` is called. This ensures the CLI path triggers artifact saving. The TUI will also get this automatically when it passes `run_dir` in options.

### `runners/__init__.py` — Exports

- Added `save_artifact` and `sanitize_filename` to imports and `__all__`

## Tests Added (5 new, in `tests/test_result_writer.py`)

| Test | What it verifies |
|------|-----------------|
| `test_sanitize_filename` | Clean IDs pass through; spaces, slashes, special chars get replaced |
| `test_save_artifact_default_extension` | `.md` used when no `artifact_extension` in task metadata |
| `test_save_artifact_custom_extension` | `.py` applied when `artifact_extension: ".py"` is set |
| `test_save_artifact_returns_absolute_path` | Return value is absolute path pointing to existing file |
| `test_save_artifact_with_special_chars_in_id` | Task IDs with `/`, `!`, spaces get sanitized in filenames |

### Existing test fix (`tests/test_benchmark_runner.py`)

- Added `"artifact_paths"` to `expected_fields` set in `test_normal_run_two_tasks_one_repeat` to match the new field in result dicts.

## Verification

- **362 tests pass** (full suite: `python -m pytest tests/ -q`)
- **Dry-run CLI works**: `python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file benchmarks/reasoning/math.jsonl --dry-run`
- New functions import correctly: `from runners.result_writer import sanitize_filename, save_artifact`

## Done Criteria Status

- [x] Coding responses are saved as separate files under `artifacts/<suite_id>/`
- [x] Raw JSONL still includes the full response (artifacts are additional copies)
- [x] Artifact paths are recorded in each raw result's `artifact_paths` field
- [x] Tests cover extension selection and path sanitization

# Phase 1 Contract

> This document defines the exact behavior of the Phase 1 benchmark harness.
> Phase 2 must build on this contract without breaking it.
> All statements are derived from the actual code — not aspirational design.

---

## 1. Valid Model Config Fields

Model configs are YAML files loaded by `runners/config_loader.py`.

### Required top-level keys

| Key | Type | Description |
|-----|------|-------------|
| `id` | string | Unique config identifier, e.g. `qwen-9b-q8-4k` |
| `model_name` | string | Human-readable model name, e.g. `Qwen3.5-9B` |
| `runtime` | dict | Connection settings (see required nested keys below) |
| `settings` | dict | Generation parameters (see required nested keys below) |

### Required nested keys

| Path | Type | Description |
|------|------|-------------|
| `runtime.server_url` | string | Full OpenAI-compatible endpoint URL, e.g. `http://127.0.0.1:8080/v1/chat/completions` |
| `settings.temperature` | float | Temperature for generation |
| `settings.top_p` | float | Top-p sampling parameter |
| `settings.max_tokens` | int | Maximum tokens in response |

### Optional fields (commonly used)

| Path | Type | Description |
|------|------|-------------|
| `model_path` | string | Local path to the model file |
| `runtime.engine` | string | Inference engine name, e.g. `llama.cpp` |
| `settings.context_size` | int | Context window size |
| `settings.gpu_layers` | int | GPU layer offload count |
| `settings.flash_attn` | bool | Whether flash attention is enabled |
| `settings.cache_type_k` | string | Key cache type, e.g. `q8_0` |
| `settings.cache_type_v` | string | Value cache type, e.g. `q8_0` |
| `hardware.gpu` | string | GPU name |
| `hardware.vram_gb` | int | Available VRAM in GB |
| `hardware.backend` | string | Compute backend, e.g. `ROCm` |

### Validation behavior

- Missing file → `FileNotFoundError`
- Invalid YAML / non-dict top-level → `ValueError`
- Missing any required top-level key → `ValueError("Missing required config key: ...")`
- Missing any required nested key → `ValueError("Missing required config key: runtime.server_url")`

---

## 2. Valid JSONL Task Fields

Tasks are JSON Lines files (one JSON object per line) loaded by `runners/task_loader.py` and validated by `runners/validators.py`.

### Required fields

| Field | Type | Validation |
|-------|------|------------|
| `id` | string or int | Must be non-empty |
| `description` | string | Must be non-empty |
| `expected_output` | string | Must be non-empty |

### Optional metadata fields

| Field | Path | Type | Purpose |
|-------|------|------|---------|
| `category` | `metadata.category` | string | Determines which scorer is used |
| `keywords` | `metadata.keywords` | list of strings | Used by `keyword_match` scorer |
| `expected_tool` | `metadata.expected_tool` | string | Used by `json_valid` scorer |
| `required_argument_keys` | `metadata.required_argument_keys` | list of strings | Used by `json_valid` scorer |
| `tolerance` | `metadata.tolerance` | float | Used by `numeric_close` scorer (default 0.01) |
| `threshold` | `metadata.threshold` | float | Used by `keyword_match` scorer (default 0.7) |
| `command` | root | string | Passed through but not executed in Phase 1 |

### Validation behavior

- Missing file → `FileNotFoundError`
- Path is a directory → `ValueError`
- Blank lines are silently skipped
- Non-JSON line → `ValueError` with line number
- Non-dict line → `ValueError` with line number
- Missing any required field → `ValueError` chaining `ValidationError`

---

## 3. Category-to-Scorer Behavior

The scorer mapping is hardcoded in `run_benchmark.py` as `CATEGORY_SCORER_MAP`:

| `metadata.category` | Scorer module | Scoring logic | Score range |
|---------------------|---------------|---------------|-------------|
| `math` | `numeric_close` | Extracts first number from response, compares to `expected_output` within `tolerance` (default 0.01) | 0 or 1 |
| `numeric` | `numeric_close` | Same as `math` | 0 or 1 |
| `text` | `exact_match` | Case-insensitive, whitespace-normalized comparison against `expected_output` | 0 or 1 |
| `general` | `exact_match` | Same as `text` | 0 or 1 |
| `keyword` | `keyword_match` | Checks fraction of `keywords` (from `metadata.keywords`) present in response (case-insensitive), requires `threshold` fraction (default 0.7) | 0.0–1.0 |
| `code` | `keyword_match` | Same as `keyword` | 0.0–1.0 |
| `json` | `json_valid` | Validates JSON parse, checks `tool` against `expected_tool`, checks `arguments` keys against `required_argument_keys` (partial credit per check) | 0.0–1.0 |
| `tool` | `json_valid` | Same as `json` | 0.0–1.0 |
| *(any other or missing)* | `exact_match` | Fallback to exact string match | 0 or 1 |

### Scorer interface

Every scorer is a function with the signature:

```python
def score(task: dict, response: str) -> dict:
    """Returns {"score": float, "passed": bool, "reason": str}"""
```

### Scorer registry

The `scorers.registry.get_scorer(name)` function maps string names to scorer callables. Registered names: `exact_match`, `numeric_close`, `keyword_match`, `json_valid`.

---

## 4. Batch CLI Arguments

The only entry point is `run_benchmark.py`. It uses `argparse` with these arguments:

| Argument | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `--config` | Yes | str | — | Path to YAML model config file |
| `--task-file` | Yes | str | — | Path to JSONL task file |
| `--dry-run` | No | flag | `False` | Load config and tasks, print task count, exit without API calls |
| `--repeats` | No | int | `1` | Number of times to repeat each task |

### Behavior notes

- `--dry-run` prints `"Dry-run: loaded N tasks"` and exits with code 0
- `--repeats N` runs each task N times, each attempt is an independent API call
- Config and task file paths are resolved relative to the working directory
- Exit codes: 0 on success, non-zero on error

---

## 5. Raw Result Object Shape

Each result is a dict produced by `_build_result` or `_build_error_result` in `run_benchmark.py`:

| Key | Type | Description |
|-----|------|-------------|
| `run_id` | str | Timestamp-based unique ID, e.g. `20260502_143000` |
| `model_config_id` | str | From config `id` field |
| `task_id` | str | From task `id` field |
| `category` | str | From `metadata.category`, or `"general"` if missing |
| `task_file` | str | Path to the source JSONL file |
| `prompt` | str | The `description` field sent as the user prompt |
| `expected` | str | The `expected_output` field |
| `response` | str | Model's response text, or error message |
| `latency_sec` | float | Wall-clock time for the API call |
| `score` | float | Scorer output (0.0–1.0) |
| `passed` | bool | Whether the attempt passed (`True` if score meets criteria) |
| `reason` | str | Scorer's human-readable explanation |
| `settings` | dict | The generation settings used (from config) |
| `repeat_index` | int | Zero-based repeat number |
| `repeat_count` | int | Total repeats configured |

### Error results

When the API call fails (`ConnectionError`, `TimeoutError`, `RuntimeError`, etc.), an error result is produced with:
- `score` = `0.0`
- `passed` = `False`  
- `response` = error message string
- `latency_sec` = `0.0`

---

## 6. Summary CSV Columns

`runners/result_writer.py` → `results/summary.csv`

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | str | Unique run identifier |
| `model_config_id` | str | Model config identifier |
| `task_file` | str | Source task file path |
| `total_tasks` | int | Number of unique task definitions |
| `total_attempts` | int | Total attempts (tasks × repeats) |
| `passed` | int | Number of passed attempts |
| `failed` | int | Number of failed attempts |
| `pass_rate` | float | `passed / total_attempts` (formatted to 4 decimal places) |
| `average_score` | float | Mean score across all attempts (formatted to 4 decimal places) |
| `average_latency_sec` | float | Mean latency in seconds (formatted to 3 decimal places) |
| `repeats` | int | Repeat count for this run |

### Behavior notes

- CSV header is auto-written on first creation
- If the existing CSV has different column headers, rows are migrated to the current schema
- File path: `results/summary.csv` (relative to working directory)

---

## 7. Leaderboard Behavior

`runners/leaderboard.py` → `results/reports/leaderboard.md`

### Processing steps

1. Read `results/summary.csv`
2. Group rows by `(model_config_id, task_file)`
3. Within each group, keep only the row with the latest `run_id` (lexicographic comparison)
4. Parse numeric fields (`total_tasks`, `total_attempts`, `pass_rate`, `average_score`, `average_latency_sec`, `repeats`)
5. Sort by:
   - **Average score** (descending)
   - **Pass rate** (descending, tiebreaker)
   - **Average latency** (ascending, tiebreaker)
6. Write Markdown table

### Leaderboard columns

| Column | Description |
|--------|-------------|
| Model Config | `model_config_id` from config |
| Task File | Source task file path |
| Total Tasks | Number of unique tasks |
| Total Attempts | Total attempts (tasks × repeats) |
| Repeats | Repeat count |
| Pass Rate | Percentage, formatted as `XX.X%` |
| Avg Score | Mean score, formatted to 2 decimal places |
| Avg Latency | Mean latency in seconds with `s` suffix |

### Empty / missing data

- If summary CSV is missing or empty: writes `"# Local Model Benchmark Leaderboard\n\nNo data yet.\n"`
- On read error: same empty output, error printed to stderr

---

## 8. Backward-Compatibility Expectations

Phase 2 **must not** change or remove:

| Area | What is frozen |
|------|----------------|
| CLI arguments | `--config`, `--task-file`, `--dry-run`, `--repeats` must continue working as documented |
| Config format | YAML schema with `id`, `model_name`, `runtime`, `settings` required keys |
| Task format | JSONL with `id`, `description`, `expected_output` required fields |
| Scorer interface | `score(task, response) → dict` signature must remain valid |
| Category mapping | Existing categories (`math`, `numeric`, `text`, `general`, `keyword`, `code`, `json`, `tool`) must map to the same scorers |
| Summary CSV columns | All 11 documented columns must be present |
| Leaderboard output format | The Markdown table structure and sorting behavior |

Phase 2 **may** extend:

- New CLI arguments (but existing ones remain)
- New config fields (but existing required fields remain required)
- New task metadata fields (but existing required fields remain required)
- New scorer categories (but existing categories remain mapped the same way)
- New summary columns (but existing columns remain)
- New result dict keys (but existing keys remain)
- New output files and directories (but existing paths remain)

### Rule of thumb

Any command that worked in Phase 1 must produce the same behavior in Phase 2.

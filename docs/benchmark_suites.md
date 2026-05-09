# Benchmark Suites

## Overview

Benchmark suites are named groups of task files organized by domain. Each suite
has a unique ID, a human-readable name, a category, and a scoring method.

Suites are registered in `benchmarks/suites.yaml` and can be run via the batch
CLI (`--suite <id>`) or selected interactively in the TUI.

---

## Available Suites

The harness includes eight built-in suites. More can be added by creating task
files and registering them in `benchmarks/suites.yaml`.

| Suite ID | Name | Category | Description | Scoring |
|----------|------|----------|-------------|---------|
| `reasoning.math` | Math | reasoning | Numeric and short-answer math prompts | deterministic |
| `reasoning.real_world` | Real-World Reasoning | reasoning | Multi-step real-world reasoning tasks | deterministic |
| `reasoning.instruction_following` | Instruction Following | reasoning | Adherence to formatting and content instructions | deterministic |
| `coding.frontend` | Frontend Coding | coding | Frontend (HTML/CSS/JS/TSX) code generation | deterministic + artifact |
| `coding.backend` | Backend Coding | coding | Backend (Python/API/database) code generation | deterministic + artifact |
| `coding.misc` | Misc Coding | coding | General scripting and algorithmic tasks | deterministic + artifact |
| `tools.json_tool_calling` | JSON Tool Calling | tools | Strict JSON tool-call generation | deterministic |
| `context.long_context` | Long Context | context | Long-context recall and retrieval tasks | deterministic |

---

## Running a Suite

### Batch CLI

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite reasoning.math
```

Or use a model ID instead of a file path:

```powershell
python run_benchmark.py --config qwen-9b-q8-4k --suite reasoning.math
```

Dry-run to inspect tasks without calling the model:

```powershell
python run_benchmark.py --config qwen-9b-q8-4k.yaml --suite coding.frontend --dry-run
```

### Terminal UI

1. Launch the TUI: `python bench_tui.py`
2. Select a model config on the Dashboard.
3. Press `s` to open Suite Selection.
4. Use arrow keys and Space to toggle suites on/off.
5. Press Enter to confirm selection.
6. Press Enter on "Run" to start.

Multiple suites can be selected and will run sequentially.

---

## Suite Registry Format

Suites are defined in `benchmarks/suites.yaml`:

```yaml
suites:
  - id: reasoning.math
    name: Math
    category: reasoning
    task_file: benchmarks/reasoning/math.jsonl
    description: Numeric and short-answer math prompts.
    scoring: deterministic
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique dot-separated identifier (`<category>.<name>`) |
| `name` | string | Human-readable display name |
| `category` | string | Grouping category (`reasoning`, `coding`, `tools`, `context`) |
| `task_file` | string | Path to JSONL task file (relative to project root) |
| `description` | string | One-line description of the suite |
| `scoring` | string | `deterministic` or `deterministic + artifact` |

---

## Adding a New Suite

1. Create a JSONL task file in the appropriate `benchmarks/<category>/` directory.
2. Add an entry to `benchmarks/suites.yaml`.
3. Verify it appears in the suite list:

   ```powershell
   python -c "from runners.suite_registry import list_suites; print(list_suites())"
   ```

4. Test it with a dry run:

   ```powershell
   python run_benchmark.py --config qwen-9b-q8-4k --suite my.new_suite --dry-run
   ```

---

## Task File Format Reference

Each suite loads tasks from a JSONL file. See [Task File Format](task_file_format.md)
for the full reference. At minimum, each task must have:

```json
{
  "id": "my_task_001",
  "description": "The prompt sent to the model",
  "expected_output": "The reference answer",
  "metadata": {
    "category": "text"
  }
}
```

Optional metadata fields (used by specific suites):

| Field | Path | Used By |
|-------|------|---------|
| `keywords` | `metadata.keywords` | keyword_match scorer (instruction following, coding suites) |
| `expected_tool` | `metadata.expected_tool` | json_valid scorer (tool calling suite) |
| `required_argument_keys` | `metadata.required_argument_keys` | json_valid scorer (tool calling suite) |
| `artifact_extension` | `metadata.artifact_extension` | Coding suites (e.g., `.tsx`, `.py`) |
| `artifact_kind` | `metadata.artifact_kind` | Coding suites (`frontend`, `backend`, `misc`) |
| `estimated_context_tokens` | `metadata.estimated_context_tokens` | Long-context suite |

---

## Official Benchmark Imports

Imported datasets from open-source benchmarks can be added under
`benchmarks/official/`. Currently supported import sources:

- GSM8K (math word problems)
- MMLU (multiple-choice knowledge)
- MBPP (Python coding)
- HumanEval (Python function completion)

See [README - Importing Official Benchmarks](../README.md#importing-official-benchmarks)
for import instructions.

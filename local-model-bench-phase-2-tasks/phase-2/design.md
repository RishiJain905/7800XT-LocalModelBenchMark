# Phase 2 Design - End-to-End Local Model Benchmark Product

## Purpose

Phase 2 turns the Phase 1 benchmark harness into a complete local benchmarking product for fine-tuned and general local models served through OpenAI-compatible endpoints such as `llama-server`.

The user is expected to start `llama-server` separately with the model they want to test. The benchmark app does not need to launch or stop `llama-server` in Phase 2. Instead, it lets the user select which saved model config matches the currently loaded server, verifies the endpoint, runs selected benchmark suites, saves raw outputs and artifacts, and updates comparison reports.

## Core User Workflow

Primary workflow:

```powershell
python bench_tui.py
```

The terminal UI should support keyboard-driven navigation:

1. Select the model config that is currently loaded in `llama-server`.
2. Check that the configured server endpoint is reachable.
3. Select one or more benchmark suites.
4. Configure run options such as repeats and max tasks.
5. Start the run.
6. Watch live progress.
7. Cancel safely if needed.
8. Resume incomplete runs later.
9. Browse previous results.

The existing batch workflow must remain available:

```powershell
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --task-file benchmarks/reasoning/math.jsonl
```

## Design Principles

- Build on Phase 1, do not replace it.
- Keep the batch CLI scriptable and stable.
- Keep the TUI as a front end over reusable runner code.
- Treat any OpenAI-compatible local server as valid.
- Do not hardcode one model, model family, GPU, or runtime.
- Save raw outputs always.
- Save coding outputs as standalone artifacts.
- Make cancellation safe.
- Make incomplete runs resumable.
- Prefer deterministic scoring before adding judge-based scoring.
- Keep dependencies reasonable and justified.
- Keep file formats simple: YAML, JSONL, JSON, CSV, Markdown.
- Keep Windows PowerShell usage first-class.

## High-Level Architecture

```text
bench_tui.py
  Keyboard-driven terminal UI.
  Calls registries, health checks, and reusable runner.

run_benchmark.py
  Batch CLI wrapper.
  Calls the same reusable runner.

runners/
  benchmark_runner.py
    Core execution engine.
  model_registry.py
    Discovers saved model configs.
  suite_registry.py
    Discovers benchmark suites.
  server_health.py
    Checks local OpenAI-compatible server status.
  result_writer.py
    Writes raw results, summaries, run manifests, and artifacts.
  leaderboard.py
    Generates comparison reports.
  config_loader.py
    Existing YAML config loader.
  task_loader.py
    Existing JSONL task loader.
  llama_client.py
    Existing OpenAI-compatible chat client.

scorers/
  Existing deterministic scorer modules.

benchmarks/
  JSONL benchmark suites grouped by domain.

configs/models/
  Saved model configs.

results/runs/
  Structured per-model run output.
```

## Model Configs

Model configs describe the model and endpoint the user says is currently loaded.

Target location:

```text
configs/models/<model_id>.yaml
```

Required fields remain compatible with Phase 1:

```yaml
id: qwen-9b-q8-4k
model_name: Qwen3.5-9B
model_path: D:/LOCAL-MODELS/Qwen3.5-9B-Q8.gguf

runtime:
  engine: llama.cpp
  server_url: http://127.0.0.1:8080/v1/chat/completions

settings:
  context_size: 4096
  temperature: 0
  top_p: 1
  max_tokens: 1024

hardware:
  gpu: RX 7800 XT
  vram_gb: 16
  backend: ROCm
```

Phase 2 should continue accepting direct config paths so old commands work.

The model registry should:

- List configs from `configs/models/`.
- Validate each config using the existing loader.
- Reject duplicate IDs.
- Return clear errors for invalid configs.

## Server Health

The benchmark should assume the server is already running, then verify it.

Health check behavior:

- Use `runtime.server_url` as the chat completions endpoint.
- Derive a likely `/v1/models` endpoint when possible.
- Try `/v1/models`, but do not require it.
- Report reachable/unreachable status clearly.
- Surface connection refused, timeout, non-200, and invalid JSON errors.

Health check result shape:

```json
{
  "reachable": true,
  "server_url": "http://127.0.0.1:8080/v1/chat/completions",
  "models_endpoint_available": true,
  "reported_models": ["local-model"],
  "error": ""
}
```

The TUI should show this status before allowing or recommending a run.

## Benchmark Suites

Suites are named groups of task files.

Target registry:

```text
benchmarks/suites.yaml
```

Example:

```yaml
suites:
  - id: reasoning.math
    name: Math
    category: reasoning
    task_file: benchmarks/reasoning/math.jsonl
    description: Numeric and short-answer math prompts.
    scoring: deterministic
```

Target suite folders:

```text
benchmarks/
  coding/
    frontend.jsonl
    backend.jsonl
    misc.jsonl
  reasoning/
    math.jsonl
    real_world.jsonl
    instruction_following.jsonl
  tools/
    json_tool_calling.jsonl
  context/
    long_context.jsonl
  official/
    README.md
```

Initial required suite coverage:

- Math.
- Real-world reasoning.
- Instruction following.
- Frontend coding.
- Backend coding.
- Misc coding.
- Tool calling / strict JSON.
- Long-context / recall.
- Optional official/open-source imports.

## Task Format

Task files remain JSONL: one JSON object per line.

Minimum valid task:

```json
{
  "id": "math_add",
  "description": "What is 2 + 2? Reply with only the number.",
  "command": "noop",
  "expected_output": "4",
  "metadata": {
    "category": "math"
  }
}
```

Important Phase 2 metadata:

```json
{
  "metadata": {
    "category": "code",
    "keywords": ["fetch", "error handling"],
    "artifact_kind": "frontend",
    "artifact_extension": ".tsx",
    "expected_tool": "get_weather",
    "required_argument_keys": ["location"],
    "estimated_context_tokens": 4096
  }
}
```

The existing `command` field is still required by the loader, but Phase 2 does not need to execute shell commands unless a future benchmark type explicitly adds sandboxed execution.

## Scoring Strategy

Keep deterministic scoring as the default:

- `exact_match` for constrained short text.
- `numeric_close` for numeric answers.
- `keyword_match` for keyword/structure checks.
- `json_valid` for strict JSON/tool-call shape.

Coding benchmarks in Phase 2 should not pretend to be fully solved by keyword scoring. They should:

- Save full outputs as artifacts.
- Apply lightweight deterministic checks.
- Clearly document that deeper coding judgment is future work unless an official benchmark has deterministic tests.

Future scoring can add:

- Unit-test execution in isolated sandboxes.
- LLM-as-judge.
- Human review workflows.

Those are not required for Phase 2 completion unless explicitly added later.

## Reusable Runner

The current `run_benchmark.py` logic should be extracted into reusable code.

Target:

```text
runners/benchmark_runner.py
```

The runner should support:

- Direct config dictionaries.
- Loaded task lists.
- Suite metadata.
- Repeats.
- Dry-run.
- Per-attempt callbacks.
- Progress callbacks.
- Result streaming.
- Cancellation.
- Resume planning.

The TUI and batch CLI should both call this runner. The TUI should not shell out to `run_benchmark.py`.

## Run Storage

Every run should have a durable run folder.

Target structure:

```text
results/runs/<model_id>/<run_id>/
  manifest.json
  raw.jsonl
  summary.json
  artifacts/
```

`manifest.json` example:

```json
{
  "run_id": "2026-05-02_14-30-00",
  "model_config_id": "qwen-9b-q8-4k",
  "model_name": "Qwen3.5-9B",
  "suite_id": "reasoning.math",
  "suite_name": "Math",
  "task_file": "benchmarks/reasoning/math.jsonl",
  "server_url": "http://127.0.0.1:8080/v1/chat/completions",
  "settings": {
    "context_size": 4096,
    "temperature": 0,
    "top_p": 1,
    "max_tokens": 1024
  },
  "status": "running",
  "started_at": "2026-05-02T14:30:00",
  "completed_at": null,
  "repeats": 1,
  "total_tasks": 20,
  "total_attempts": 20
}
```

Allowed statuses:

- `running`
- `completed`
- `cancelled`
- `failed`

`raw.jsonl` should contain one JSON object per completed attempt. Write each result immediately after the attempt completes.

`summary.json` should contain aggregate data for the run.

The existing `results/summary.csv` and `results/reports/leaderboard.md` should continue to update for easy comparison.

## Coding Artifacts

For coding tasks, save model responses to standalone files under:

```text
results/runs/<model_id>/<run_id>/artifacts/<suite_id>/
```

Example:

```text
artifacts/coding.frontend/frontend_component_001_response.tsx
artifacts/coding.backend/api_handler_001_response.py
```

Rules:

- Use `metadata.artifact_extension` when provided.
- Default to `.md`.
- Sanitize task IDs before using them in filenames.
- Record artifact paths in the raw result object.
- Never remove the response from `raw.jsonl`; artifacts are additional.

## Interrupt Safety

Runs must be safe to cancel.

Requirements:

- Create run folder and manifest before model calls.
- Append each completed attempt to `raw.jsonl` immediately.
- Flush writes after each result.
- On Ctrl+C or TUI cancellation, mark manifest `cancelled`.
- Leave completed results readable.
- Write partial summary from completed attempts.

This matters because users may stop the benchmark, restart `llama-server`, or switch models.

## Resume Behavior

Resume should continue an incomplete run without repeating completed attempts.

Batch example:

```powershell
python run_benchmark.py --resume results/runs/qwen-9b-q8-4k/2026-05-02_14-30-00
```

Resume algorithm:

1. Read `manifest.json`.
2. Read `raw.jsonl`.
3. Build a set of completed `(task_id, repeat_index)` attempts.
4. Reload the original task file.
5. Skip completed attempts.
6. Run missing attempts.
7. Append new results to the same `raw.jsonl`.
8. Update summary and manifest status.

Handle corrupted or incomplete raw lines gracefully by reporting a clear error or skipping only if safe.

## Terminal UI

The UI should be keyboard/menu driven, not a question-by-question wizard.

Target entry point:

```powershell
python bench_tui.py
```

Target smoke check:

```powershell
python bench_tui.py --smoke-test
```

Recommended implementation:

- Prefer `textual` for a polished keyboard-driven app.
- Use `rich` where helpful for formatting tables/progress.

Required screens:

- Dashboard.
- Model selection.
- Benchmark suite selection.
- Run settings.
- Live run progress.
- Results browser.

Required keyboard behavior:

- Arrow keys move selection.
- Enter confirms.
- Escape backs out.
- A clear key or command cancels a running benchmark.

Dashboard should show:

- Selected model.
- Server status.
- Selected suite count.
- Last run summary.
- Available actions.

Run progress should show:

- Current suite.
- Current task.
- Completed attempts / total attempts.
- Latest score.
- Latest latency.
- Output folder.
- Cancellation state.

## Official/Open-Source Benchmarks

Official benchmark support should be optional and modular.

Recommended first targets:

- GSM8K-style math subset.
- HumanEval or MBPP-style coding subset if licensing/access is acceptable.
- MMLU-style multiple-choice subset if practical.

Importer behavior:

- Convert source data into this harness's JSONL task format.
- Preserve source attribution in metadata.
- Allow `--limit`.
- Avoid committing large downloaded datasets.
- Provide clear skip/error messages when data is unavailable.

Example:

```powershell
python scripts/import_benchmark.py --source gsm8k --limit 50 --output benchmarks/official/gsm8k_sample.jsonl
```

## Summary and Leaderboard

Existing outputs remain:

```text
results/summary.csv
results/reports/leaderboard.md
```

Add per-run:

```text
results/runs/<model_id>/<run_id>/summary.json
```

Summary should include:

- `run_id`
- `model_config_id`
- `model_name`
- `suite_id`
- `suite_name`
- `task_file`
- `run_folder`
- `status`
- `total_tasks`
- `total_attempts`
- `passed`
- `failed`
- `pass_rate`
- `average_score`
- `average_latency_sec`
- `repeats`
- `artifact_count`
- `started_at`
- `completed_at`

Leaderboard should compare latest runs by model and suite, sorted by:

1. Highest average score.
2. Highest pass rate.
3. Lowest average latency.

## Testing Strategy

Use tests to protect every core behavior:

- Config registry.
- Suite registry.
- Server health checks with mocked HTTP.
- Reusable runner behavior.
- Result streaming.
- Manifest creation and status updates.
- Artifact saving.
- Cancellation.
- Resume planning.
- Summary and leaderboard generation.
- TUI smoke test.
- Benchmark file validation.
- Importer conversion with tiny fixtures.

Minimum final verification:

```powershell
python -m pytest tests/ -q
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --dry-run
python bench_tui.py --smoke-test
```

With `llama-server` running, manually verify at least one real run from both:

```powershell
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --repeats 1
python bench_tui.py
```

## Backward Compatibility

Do not break:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl --dry-run
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl --repeats 3
```

New features should extend this CLI, not remove it.

## Phase 2 Done Definition

Phase 2 is done when:

- The TUI launches and supports keyboard-driven selection.
- The user can select a model config for an already-running `llama-server`.
- Server health status is visible.
- The user can select benchmark suites.
- Runs save under `results/runs/<model_id>/<run_id>/`.
- Raw outputs, summaries, manifests, and coding artifacts are preserved.
- Cancellation does not lose completed results.
- Resume skips completed attempts.
- Batch CLI still works.
- Summaries and leaderboards update.
- README and docs explain real usage.
- Automated tests pass.
- At least one real local model run has been manually validated.


# How to Run Local Model Benchmarks

This guide explains how to start the benchmark app and test local models served by an OpenAI-compatible server such as `llama-server`.

## 1. Install Dependencies

From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Start Your Local Model Server

Start `llama-server` separately before running a real benchmark. Example:

```powershell
llama-server.exe -m "D:\LOCAL-MODELS\your-model.gguf" -ngl 99 -c 4096 --flash-attn on --port 8080
```

The benchmark expects an OpenAI-compatible chat completions endpoint like:

```text
http://127.0.0.1:8080/v1/chat/completions
```

Keep this terminal open while benchmarks run.

## 3. Configure the Model

Model configs live in:

```text
configs/models/
```

Use the existing example as a template:

```text
configs/models/qwen-9b-q8-4k.yaml
```

Important fields:

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
```

Make sure `runtime.server_url` matches the server you started.

## 4. Quick Validation

Run these before a real benchmark:

```powershell
python -m pytest tests/ -q
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --dry-run
python bench_tui.py --smoke-test
```

The dry run checks config, suite, tasks, and scorers without calling the model.

## 5. Run From the Terminal UI

Launch the keyboard-driven app:

```powershell
python bench_tui.py
```

Typical flow:

1. Select the model config that matches the currently running server.
2. Run the health check.
3. Select one or more benchmark suites.
4. Set repeats and max tasks if needed.
5. Start the run.
6. Watch progress.
7. Open the results browser to inspect previous runs.

Useful keys:

| Key | Action |
|-----|--------|
| `m` | Select model |
| `h` | Check server health |
| `s` | Select benchmark suites |
| `o` | Edit run settings |
| Enter | Confirm or start selected action |
| Escape | Go back |
| `b` | Browse results |
| `c` | Cancel a running benchmark |
| `r` | Resume a selected incomplete run |
| `q` | Quit |

## 6. Run From the CLI

Run a named suite:

```powershell
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --repeats 1
```

Run a direct task file:

```powershell
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --task-file benchmarks/reasoning/math.jsonl
```

Resume an interrupted run:

```powershell
python run_benchmark.py --resume results/runs/qwen-9b-q8-4k/<run_id>
```

## 7. Available Built-In Suites

Suites are registered in:

```text
benchmarks/suites.yaml
```

Current suite IDs:

```text
reasoning.math
reasoning.real_world
reasoning.instruction_following
coding.frontend
coding.backend
coding.misc
tools.json_tool_calling
context.long_context
```

For a first real run, start with `reasoning.math` because it is short and deterministic.

## 8. Read Results

Each run saves under:

```text
results/runs/<model_id>/<run_id>/
```

Key files:

| File | Purpose |
|------|---------|
| `manifest.json` | Run metadata, config, suite, status, timestamps |
| `raw.jsonl` | One raw record per completed attempt |
| `summary.json` | Per-run aggregate metrics |
| `artifacts/` | Saved coding outputs for coding suites |

Comparison files:

```text
results/summary.csv
results/reports/leaderboard.md
```

## 9. Testing Multiple Local Models

For each model:

1. Start `llama-server` with that model.
2. Create or update a matching config in `configs/models/`.
3. Confirm the config `id` is unique.
4. Run the same suite against each model.
5. Compare `results/reports/leaderboard.md`.

Example:

```powershell
python run_benchmark.py --config configs/models/model-a.yaml --suite reasoning.math --repeats 1
python run_benchmark.py --config configs/models/model-b.yaml --suite reasoning.math --repeats 1
```

## Troubleshooting

If health check fails:

- Confirm `llama-server` is running.
- Confirm the port matches `runtime.server_url`.
- Open `http://127.0.0.1:8080/v1/models` in a browser if the server supports it.
- Check that no firewall or existing process is blocking the port.

If a run is cancelled:

- Completed attempts stay in `raw.jsonl`.
- Resume from the TUI results browser with `r`, or use `--resume`.

If coding scores look too simple:

- That is expected for Phase 2.
- Coding outputs are saved as artifacts for manual review.
- Full sandboxed code execution is future work.

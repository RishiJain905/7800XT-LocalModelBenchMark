# Task 10 — Write README Usage Documentation

## Goal

Write complete usage documentation so a fresh user can run the Phase 1 benchmark harness.

## Required file

Update:

```text
README.md
```

## README must include

### 1. Project description

Explain that this is a lightweight benchmark harness for local LLMs and runtime settings.

Mention that it is designed around local OpenAI-compatible endpoints such as `llama-server`.

### 2. Installation

Example:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Starting llama-server

Include an example command placeholder, but do not make it overly specific.

Example:

```powershell
llama-server.exe -m "D:\LOCAL-MODELS\your-model.gguf" -ngl 99 -c 4096 --flash-attn on --port 8080
```

Mention that the config file should point to:

```text
http://127.0.0.1:8080/v1/chat/completions
```

### 4. Model config format

Show the YAML config example.

### 5. Task file format

Show JSONL examples for:

- exact answer
- numeric answer
- keyword answer
- JSON/tool format answer

### 6. Running a benchmark

Example:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl
```

### 7. Running repeats

Example:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl --repeats 3
```

### 8. Dry run

Example:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl --dry-run
```

### 9. Results layout

Explain:

```text
results/raw/
results/summary.csv
results/reports/leaderboard.md
```

### 10. What Phase 1 does and does not include

Phase 1 includes:

- basic local model benchmarking
- simple scorers
- raw result saving
- summary CSV
- markdown leaderboard
- repeat-run support

Phase 1 does not yet include:

- full Hermes Agent benchmark
- real file-editing coding benchmark
- browser/tool sandbox
- advanced dashboards
- LLM-as-judge scoring

## Done criteria

This task is done when:

- README is complete enough for a fresh user to run the benchmark.
- README includes install, config, task, run, results, and limitation sections.
- All Phase 1 tasks have been completed.

## Final Phase 1 verification

Run:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl --dry-run
```

Then, with `llama-server` running:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file tasks/math/basic_math.jsonl --repeats 1
```

Confirm that these files exist:

```text
results/raw/<model_config_id>/*.jsonl
results/summary.csv
results/reports/leaderboard.md
```

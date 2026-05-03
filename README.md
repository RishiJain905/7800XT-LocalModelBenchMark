# Local Model Benchmark Harness

A lightweight, reproducible benchmark harness for evaluating local LLMs served through OpenAI-compatible endpoints (e.g. `llama.cpp` / `llama-server`). Design your own task files, run them against any model, and compare results across configurations in a unified leaderboard.

---

## Quick Start

### 1. Install

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start llama-server

Launch your model with `llama-server`:

```powershell
llama-server.exe -m "D:\LOCAL-MODELS\your-model.gguf" -ngl 99 -c 4096 --flash-attn on --port 8080
```

The server exposes an OpenAI-compatible chat completions endpoint at:

```
http://127.0.0.1:8080/v1/chat/completions
```

### 3. Run a benchmark

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl
```

---

## Model Configuration

Model settings are defined in **YAML config files** under `configs/`. Each config describes the model, server endpoint, and generation parameters.

**Example** (`configs/qwen-9b-q8-4k.yaml`):

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

| Field | Description |
|-------|-------------|
| `id` | Short identifier used in results and the leaderboard |
| `model_name` | Human-readable model name |
| `runtime.server_url` | OpenAI-compatible chat completions endpoint |
| `settings` | Generation parameters (temperature, top_p, max_tokens, etc.) |
| `hardware` | Optional hardware metadata for reference |

---

## Task File Format

Tasks are defined in **JSONL (JSON Lines)** format — one JSON object per line. Each task has a `description` (the prompt sent to the model) and an `expected_output` (the reference answer used for scoring).

### Exact Answer

Used for prompts where the model must produce a verbatim match.

```jsonl
{"id": "math_add", "description": "What is 2 + 2?", "expected_output": "4", "metadata": {"category": "text"}}
```

**Scorer**: `exact_match` — case-insensitive, whitespace-normalized comparison.

### Numeric Answer

Used for numerical reasoning where a small tolerance is acceptable.

```jsonl
{"id": "math_pi", "description": "What is the value of pi to 2 decimal places?", "expected_output": "3.14", "metadata": {"category": "math"}}
```

**Scorer**: `numeric_close` — extracts the first number from the response and compares within a tolerance (default `0.01`).

### Keyword Answer

Used for open-ended questions where certain keywords must appear.

```jsonl
{"id": "gen_ai", "description": "What is a transformer in ML?", "expected_output": "attention", "metadata": {"category": "keyword", "keywords": ["attention", "self-attention", "encoder", "decoder"]}}
```

**Scorer**: `keyword_match` — checks what fraction of the `keywords` list appear in the response (case-insensitive, default threshold `0.7`).

### JSON / Tool Format Answer

Used for structured output or function-calling tasks.

```jsonl
{"id": "tool_weather", "description": "Get the weather for Tokyo", "expected_output": "get_weather", "metadata": {"category": "json", "expected_tool": "get_weather", "required_argument_keys": ["location"]}}
```

**Scorer**: `json_valid` — validates that the response is valid JSON, contains the expected tool/arguments, and returns partial credit for partially correct responses.

The `metadata.category` field determines which scorer is used. Custom mappings are defined in `CATEGORY_SCORER_MAP` inside `run_benchmark.py`.

### Coding Benchmark Suites

Coding suites are available through `benchmarks/suites.yaml`:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite coding.frontend --dry-run
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite coding.backend --dry-run
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite coding.misc --dry-run
```

Phase 2 coding scores are lightweight keyword and structure checks. They are useful for quick smoke comparisons, but they are not a full coding judge. Full model responses are always preserved for manual inspection, and coding outputs are also saved as standalone artifacts under:

```text
results/runs/<model_id>/<run_id>/artifacts/<suite_id>/
```

Stronger coding evaluation with sandboxed tests or LLM-as-judge scoring is future work.

---

## Usage

### Basic run

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl
```

### Run with repeats (reduce noise)

Each task is run N times to measure response consistency:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl --repeats 3
```

Default is `--repeats 1`. When `--repeats 3` is used, each task runs 3 times and raw results include `repeat_index` and `repeat_count` metadata.

### Dry run (inspect without calling the model)

Inspect which tasks and scorers would be used without sending any requests:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl --dry-run
```

---

## Results

After a benchmark run, results are written to the `results/` directory:

```
results/
├── raw/<model_config_id>/          # Per-task raw results (JSONL)
│   └── <task_file_stem>_<run_id>.jsonl
├── summary.csv                     # Aggregated summary across all runs
└── reports/
    └── leaderboard.md              # Markdown leaderboard
```

### Raw results

One JSON object per task attempt, including the prompt, model response, score, latency, and repeat metadata (when `--repeats > 1`):

```json
{
  "task_id": "math_add",
  "repeat_index": 0,
  "repeat_count": 3,
  "score": 1.0,
  "passed": true,
  "latency_sec": 1.23,
  "response": "4",
  ...
}
```

### Summary CSV

Columns:

| Column | Description |
|--------|-------------|
| `run_id` | Timestamp of the run |
| `model_config_id` | Reference to the YAML config used |
| `task_file` | Source task file |
| `total_tasks` | Number of unique task definitions |
| `total_attempts` | Total task executions (tasks × repeats) |
| `passed` | Number of passed attempts |
| `failed` | Number of failed attempts |
| `pass_rate` | passed / total_attempts |
| `average_score` | Mean score across all attempts |
| `average_latency_sec` | Mean latency in seconds |
| `repeats` | Repeat count used for this run |

### Leaderboard

Generated automatically after each run. Ranks model configurations by average score, pass rate, and latency. View at `results/reports/leaderboard.md`.

---

## Phase 1 Scope

### Included

- Local model benchmark harness with YAML configs and JSONL task files
- OpenAI-compatible API client (`llama-server`, vLLM, etc.)
- Four deterministic scorers: exact match, numeric close, keyword match, JSON valid
- Per-task raw result persistence (JSONL)
- Aggregated summary CSV with pass rate, average score, and latency
- Markdown leaderboard with automatic deduplication and sorting
- Repeat-run support for noise reduction (`--repeats N`)

### Not yet included (future phases)

- Full Hermes Agent benchmark integration
- Real file-editing coding benchmark
- Browser / tool sandbox isolation
- Interactive dashboards or visualizations
- LLM-as-judge scoring (e.g., GPT-4 evaluation)
- Distributed execution across multiple machines

---

## Development

### Running tests

```powershell
python -m pytest tests/ -v
```

### Project structure

```
├── run_benchmark.py           # Main CLI entry point
├── runners/
│   ├── config_loader.py       # YAML config loading
│   ├── task_loader.py         # JSONL task loading
│   ├── llama_client.py        # OpenAI-compatible API client
│   ├── result_writer.py       # Raw results + summary CSV
│   └── leaderboard.py         # Markdown leaderboard generator
├── scorers/
│   ├── exact_match.py         # Exact text match scorer
│   ├── numeric_close.py       # Numeric tolerance scorer
│   ├── keyword_match.py       # Keyword presence scorer
│   ├── json_valid.py          # JSON tool format scorer
│   └── registry.py            # Scorer lookup registry
├── configs/                   # YAML model configs
├── data/tasks/                # Sample task files (JSONL)
├── tests/                     # Pytest test suite
└── results/                   # Benchmark output (auto-generated)
```

# Model Configurations

## Overview

Model configs are YAML files that describe the model and server endpoint the
benchmark harness calls. Each config maps to a running `llama-server` (or any
OpenAI-compatible server) instance.

Config files live under `configs/models/` and are registered by the
[model registry](../runners/model_registry.py).

---

## File Location

```
configs/models/<model_id>.yaml
```

The `<model_id>` must match the `id` field inside the file and be unique across
all configs. The model ID is also used as the directory name under
`results/runs/` for storing run output.

---

## Required Fields

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `id` | string | `qwen-9b-q8-4k` | Short kebab-case identifier. Used in results, leaderboard, and run folder names. |
| `model_name` | string | `Qwen3.5-9B` | Human-readable name for display in the TUI and reports. |
| `runtime.server_url` | string | `http://127.0.0.1:8080/v1/chat/completions` | Full OpenAI-compatible chat completions endpoint. |
| `settings.temperature` | float | `0` | Sampling temperature. Set to `0` for deterministic output. |
| `settings.top_p` | float | `1` | Nucleus sampling parameter. |
| `settings.max_tokens` | int | `1024` | Maximum tokens in the generated response. |

---

## Optional Fields

| Path | Type | Description |
|------|------|-------------|
| `model_path` | string | Local filesystem path to the model file (informational). |
| `runtime.engine` | string | Inference engine name, e.g. `llama.cpp`. |
| `settings.context_size` | int | Context window size in tokens, e.g. `4096`. |
| `settings.gpu_layers` | int | Number of layers offloaded to GPU (for reference). |
| `settings.flash_attn` | bool | Whether flash attention is enabled. |
| `settings.cache_type_k` | string | Key-value cache type, e.g. `q8_0`. |
| `settings.cache_type_v` | string | Key-value cache type for values. |
| `hardware.gpu` | string | GPU name, e.g. `RX 7800 XT`. |
| `hardware.vram_gb` | int | Available VRAM in GB. |
| `hardware.backend` | string | Compute backend, e.g. `ROCm`, `CUDA`. |

---

## Example Config

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

---

## Creating a New Config

1. Start `llama-server` (or your OpenAI-compatible server) with the desired model.
2. Note the server URL (typically `http://127.0.0.1:8080/v1/chat/completions`).
3. Create a new YAML file at `configs/models/<your-model-id>.yaml`.
4. Fill in the required fields. At minimum: `id`, `model_name`, `runtime.server_url`,
   `settings.temperature`, `settings.top_p`, and `settings.max_tokens`.
5. Verify the config loads correctly:

   ```powershell
   python -c "from runners.model_registry import list_model_configs; print(list_model_configs())"
   ```

---

## Config Validation

The model registry validates configs when they are loaded:

| Condition | Result |
|-----------|--------|
| File not found | `FileNotFoundError` |
| Invalid YAML / non-dict top-level | `ValueError` |
| Missing required key (`id`, `model_name`, `runtime`, `settings`) | `ValueError("Missing required config key: ...")` |
| Missing nested required key (`runtime.server_url`, etc.) | `ValueError("Missing required config key: runtime.server_url")` |
| Duplicate `id` across files | `ValueError("Duplicate model config id: ...")` |

---

## Backward Compatibility

In addition to `configs/models/<id>.yaml`, the batch CLI also accepts a direct
path to any YAML file:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file data/tasks/task_01.jsonl
```

This works even if the config is not inside `configs/models/`. The model
registry (used by the TUI) only scans `configs/models/`, so configs outside
that directory are not available for TUI selection but are still valid for the
batch CLI.

---

## Model Configs and llama-server

The model config's `runtime.server_url` must point to a running server. The
benchmark does not start or stop `llama-server`. Typical startup:

```powershell
llama-server.exe -m "D:\LOCAL-MODELS\your-model.gguf" -ngl 99 -c 4096 --port 8080
```

The config's `id` is just a label — it does not need to match the model file
name. Use whatever identifier is meaningful for comparing runs.

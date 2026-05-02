# Task 02 — Define Model Config Format

## Goal

Create a YAML-based model config format so every model/runtime setting can be reproduced exactly.

The benchmark must compare not only different models, but also different runtime settings of the same model.

## Required example config

Create:

```text
configs/qwen-9b-q8-4k.yaml
```

With this structure:

```yaml
id: qwen-9b-q8-4k
model_name: Qwen3.5-9B
model_path: D:/LOCAL-MODELS/Qwen3.5-9B-Q8.gguf

runtime:
  engine: llama.cpp
  server_url: http://127.0.0.1:8080/v1/chat/completions

settings:
  context_size: 4096
  gpu_layers: 99
  flash_attn: true
  cache_type_k: q8_0
  cache_type_v: q8_0
  temperature: 0
  top_p: 1
  max_tokens: 1024

hardware:
  gpu: RX 7800 XT
  vram_gb: 16
  backend: ROCm
```

## Required implementation

Create:

```text
runners/config_loader.py
```

It should expose:

```python
def load_config(path: str) -> dict:
    ...
```

Requirements:

- Load YAML using `PyYAML`.
- Validate that required top-level keys exist:
  - `id`
  - `model_name`
  - `runtime`
  - `settings`
- Validate that `runtime.server_url` exists.
- Validate that `settings.temperature`, `settings.top_p`, and `settings.max_tokens` exist.
- Raise a clear `ValueError` if anything is missing.

## Why this matters

Do not allow vague benchmark results like:

```text
Qwen 9B was faster than Qwen 18B.
```

The benchmark should produce specific results like:

```text
Qwen3.5-9B Q8, 4k context, q8 KV, flash-attn on, llama.cpp ROCm, max_tokens 1024.
```

## Done criteria

This task is done when:

- `configs/qwen-9b-q8-4k.yaml` exists.
- `runners/config_loader.py` exists.
- The config loader can load the YAML.
- Missing required fields raise clear errors.

Optional manual test:

```python
from runners.config_loader import load_config

config = load_config("configs/qwen-9b-q8-4k.yaml")
print(config["id"])
```

Expected output:

```text
qwen-9b-q8-4k
```

# Task 04 - Create Model Registry

## Goal

Support selecting any local OpenAI-compatible model configuration without editing code.

## Required files

Create:

```text
runners/model_registry.py
configs/models/
```

Move or copy the existing sample config into:

```text
configs/models/qwen-9b-q8-4k.yaml
```

Keep backward compatibility with direct `--config` paths.

## Required behavior

The registry should expose:

```python
def list_model_configs() -> list[dict]:
    ...

def get_model_config(model_id: str) -> dict:
    ...
```

Model configs should remain OpenAI-compatible endpoint configs. They should not assume only one model family or only one runtime.

## Done criteria

- Multiple model configs can exist under `configs/models/`.
- The app can list model IDs and human-readable model names.
- Direct path configs still work.
- Tests cover listing, lookup, duplicate IDs, and invalid configs.


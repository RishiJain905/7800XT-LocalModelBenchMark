# Task 04 — Build llama-server API Client ✅ DONE

## Status

**Completed** — `runners/llama_client.py` implemented and verified against spec.

## What Was Delivered

- **File created**: `runners/llama_client.py`
- **Function exposed**: `run_prompt(config: dict, prompt: str) -> dict`

## Implementation Summary

| Requirement | Implementation |
|---|---|
| Read `server_url` from config | `config["runtime"]["server_url"]` |
| Read generation settings | `temperature`, `top_p`, `max_tokens` from `config["settings"]` |
| OpenAI-compatible POST | `requests.post()` with `messages`, `temperature`, `top_p`, `max_tokens` payload |
| Latency measurement | `time.perf_counter()` bracketing the HTTP call |
| Response parsing | `raw_response["choices"][0]["message"]["content"]` |
| Return format | `{"response", "latency_sec", "usage", "raw_response"}` |
| Connection refused | Raises `ConnectionError` with server URL context |
| Timeout | Raises `TimeoutError` (120s default) |
| Non-200 HTTP | Raises `RuntimeError` with status code and body |
| Missing JSON fields | Raises `KeyError` with available keys listed |
| Token usage (optional) | Extracted from `raw_response.get("usage", {})` |

## Manual Test

Start `llama-server` locally, then run:

```python
from runners.config_loader import load_config
from runners.llama_client import run_prompt

config = load_config("configs/qwen-9b-q8-4k.yaml")
result = run_prompt(config, "Say hello in one sentence.")
print(result["response"])
print(result["latency_sec"])
```

## Notes

- Style matches existing `runners/config_loader.py` (docstrings, type hints, PEP 8)
- No new dependencies added (`requests` already in `requirements.txt`)
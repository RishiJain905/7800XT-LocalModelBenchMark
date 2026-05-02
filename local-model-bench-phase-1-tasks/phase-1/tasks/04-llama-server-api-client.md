# Task 04 — Build llama-server API Client

## Goal

Create a Python client that sends prompts to a local `llama-server` OpenAI-compatible chat completions endpoint.

This client is the bridge between the benchmark harness and the local model.

## Required file

Create:

```text
runners/llama_client.py
```

## Required function

Expose:

```python
def run_prompt(config: dict, prompt: str) -> dict:
    ...
```

## Required behavior

The function should:

1. Read the server URL from:

```python
config["runtime"]["server_url"]
```

2. Read generation settings from:

```python
config["settings"]
```

3. Send a POST request using the OpenAI-compatible chat completions format:

```json
{
  "messages": [
    {"role": "user", "content": "..."}
  ],
  "temperature": 0,
  "top_p": 1,
  "max_tokens": 1024
}
```

4. Measure latency using `time.perf_counter()`.

5. Parse the model response from:

```python
response_json["choices"][0]["message"]["content"]
```

6. Return a structured dictionary:

```json
{
  "response": "model response here",
  "latency_sec": 1.234,
  "usage": {},
  "raw_response": {}
}
```

## Error handling

Handle these cases clearly:

- Connection refused
- Timeout
- Non-200 HTTP status
- Missing expected JSON fields

Use clear Python exceptions with useful messages.

## Recommended timeout

Use a default timeout of 120 seconds.

## Optional enhancement

If `llama-server` returns token usage, include it in the result.

For example:

```json
"usage": {
  "prompt_tokens": 100,
  "completion_tokens": 50,
  "total_tokens": 150
}
```

Do not require this field to exist because some local servers may not return it consistently.

## Done criteria

This task is done when:

- `runners/llama_client.py` exists.
- `run_prompt(config, prompt)` sends a request to `llama-server`.
- It returns response text and latency.
- It gives clear errors if the server is not running.

## Manual test

Start your local server separately, then test:

```python
from runners.config_loader import load_config
from runners.llama_client import run_prompt

config = load_config("configs/qwen-9b-q8-4k.yaml")
result = run_prompt(config, "Say hello in one sentence.")
print(result["response"])
print(result["latency_sec"])
```

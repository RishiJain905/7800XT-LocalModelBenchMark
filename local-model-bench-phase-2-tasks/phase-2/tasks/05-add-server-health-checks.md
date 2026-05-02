# Task 05 - Add Server Health Checks

## Goal

Fail fast when the selected local model server is unreachable or misconfigured.

## Required file

Create:

```text
runners/server_health.py
```

## Required behavior

Expose:

```python
def check_server(config: dict) -> dict:
    ...
```

The result should include:

```json
{
  "reachable": true,
  "server_url": "http://127.0.0.1:8080/v1/chat/completions",
  "models_endpoint_available": true,
  "reported_models": ["..."],
  "error": ""
}
```

The health check should:

- Validate the configured chat completions endpoint is reachable enough to proceed.
- Try `/v1/models` when derivable from `server_url`.
- Not require `/v1/models` to exist.
- Return clear errors for connection refused, timeout, and non-JSON responses.

## Done criteria

- Health check runs before interactive benchmark execution.
- Health check can be called independently from tests.
- Tests cover reachable, unreachable, timeout, and missing `/v1/models`.


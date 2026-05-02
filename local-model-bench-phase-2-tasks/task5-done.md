# Task 05 — Add Server Health Checks ✅

## Deliverables

### Created Files

| File | Purpose |
|------|---------|
| `runners/server_health.py` | Server health check module with `check_server(config) -> dict` |
| `tests/test_server_health.py` | 20 tests covering reachable/unreachable servers, timeout, connection refused, fallback, URL derivation, and malformed configs |

### Modified Files

| File | Changes |
|------|---------|
| `runners/__init__.py` | Exports `check_server` from `server_health` |

### Done Criteria

| Criteria | Status |
|----------|--------|
| Health check runs before interactive benchmark execution (callable independently) | ✅ `check_server(config)` is a pure function callable from anywhere |
| Health check can be called independently from tests | ✅ 20 tests call it directly with mocked HTTP |
| Tests cover reachable with `/v1/models` | ✅ `test_reachable_with_models_endpoint`, `test_empty_reported_models`, `test_multiple_reported_models` |
| Tests cover reachable without `/v1/models` | ✅ `test_reachable_without_models_endpoint_404`, `test_reachable_models_500`, `test_non_json_response_from_models`, `test_models_missing_data_key` |
| Tests cover unreachable (connection refused) | ✅ `test_connection_refused` |
| Tests cover timeout | ✅ `test_timeout` |
| Tests cover fallback to chat completions | ✅ `test_fallback_to_chat_completions`, `test_fallback_succeeds_after_timeout`, `test_fallback_post_returns_404_but_server_reachable` |
| Tests cover URL derivation | ✅ `test_derived_models_url`, `test_server_url_without_chat_completions_path`, `test_server_url_trailing_slash_derivation` |
| Tests cover missing/malformed config | ✅ `test_missing_server_url`, `test_missing_runtime_key`, `test_empty_config`, `test_server_url_empty_string` |

## Health Check Architecture

```
config -> check_server(config)
           |
           +-- runtime.server_url missing? -> unreachable + error message
           |
           +-- Derive /v1/models URL from server_url
           |     (handles /v1/chat/completions and /v1/chat/completions/)
           |
           +-- GET /v1/models (10s timeout)
           |     |
           |     +-- 200 + valid JSON w/ "data" -> reachable, models_endpoint_available
           |     +-- 4xx/5xx -> reachable, no models endpoint
           |     +-- Invalid JSON -> reachable, no models endpoint
           |     +-- ConnectionError/Timeout -> fallback
           |
           +-- Fallback: POST chat/completions (max_tokens=1, "ping")
                 |
                 +-- Success -> reachable, no models endpoint
                 +-- Failure -> unreachable + error from primary check
```

## Verification

```
python -m pytest tests/test_server_health.py -q -v
20 passed in 0.20s

python -m pytest tests/ -q
323 passed in 0.75s
```

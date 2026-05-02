"""Health-check utilities for an OpenAI-compatible local model server.

Exposed API:
    check_server(config: dict) -> dict
"""

from __future__ import annotations

from typing import Any

import requests

# Shorter timeout for health checks — we want fast feedback.
_HEALTH_TIMEOUT = 10


def check_server(config: dict) -> dict:
    """Check whether an OpenAI-compatible server is reachable and healthy.

    Performs a primary check against ``/v1/models`` (derived from the
    ``server_url`` in *config*) and, if that fails with a connection or
    timeout error, falls back to a lightweight POST against the chat
    completions endpoint.

    Args:
        config: Validated configuration dict (as returned by
            :func:`~runners.config_loader.load_config`).  Must contain
            ``config["runtime"]["server_url"]``.

    Returns:
        A dict with the following keys:

        - **reachable** (*bool*): ``True`` if the server responded
          successfully to at least one check.
        - **server_url** (*str*): The ``server_url`` extracted from
          *config* (empty string if missing).
        - **models_endpoint_available** (*bool*): ``True`` if ``/v1/models``
          returned valid JSON with a ``data`` key.
        - **reported_models** (*list[str]*): Model IDs reported by
          ``/v1/models`` (empty list if unavailable).
        - **error** (*str*): Descriptive error message on failure, empty
          string on success.
    """
    # ------------------------------------------------------------------
    # Validate config structure
    # ------------------------------------------------------------------
    runtime: dict = config.get("runtime", {})
    server_url: str = runtime.get("server_url", "")

    if not server_url:
        return {
            "reachable": False,
            "server_url": server_url,
            "models_endpoint_available": False,
            "reported_models": [],
            "error": "Missing 'runtime.server_url' in config — cannot check server.",
        }

    # ------------------------------------------------------------------
    # Derive /v1/models URL from server_url
    # ------------------------------------------------------------------
    models_url = _derive_models_url(server_url)

    # ------------------------------------------------------------------
    # Primary check: GET /v1/models
    # ------------------------------------------------------------------
    if models_url:
        try:
            resp = requests.get(models_url, timeout=_HEALTH_TIMEOUT)
        except requests.exceptions.ConnectionError as exc:
            # Server unreachable — fall back to chat completions check.
            return _fallback_check(
                server_url, f"Connection refused at {server_url}: {exc}"
            )
        except requests.exceptions.Timeout as exc:
            return _fallback_check(
                server_url,
                f"Connection timed out after {_HEALTH_TIMEOUT}s at {models_url}: {exc}",
            )

        # Server responded — parse the result.
        if resp.status_code != 200:
            return {
                "reachable": True,
                "server_url": server_url,
                "models_endpoint_available": False,
                "reported_models": [],
                "error": "",
            }

        try:
            data: dict[str, Any] = resp.json()
        except ValueError:
            # Invalid JSON — server is reachable but /v1/models is broken.
            return {
                "reachable": True,
                "server_url": server_url,
                "models_endpoint_available": False,
                "reported_models": [],
                "error": "",
            }

        if "data" not in data:
            return {
                "reachable": True,
                "server_url": server_url,
                "models_endpoint_available": False,
                "reported_models": [],
                "error": "",
            }

        reported_models: list[str] = [m.get("id", "") for m in data["data"]]
        return {
            "reachable": True,
            "server_url": server_url,
            "models_endpoint_available": True,
            "reported_models": reported_models,
            "error": "",
        }

    # ------------------------------------------------------------------
    # /v1/models URL not derivable — fall back to chat completions
    # ------------------------------------------------------------------
    return _fallback_check(server_url, "")


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _derive_models_url(server_url: str) -> str:
    """Derive a ``/v1/models`` URL from *server_url*.

    Returns an empty string if the URL cannot be derived (i.e. the
    *server_url* does not end with ``/v1/chat/completions``).
    """
    # Handle trailing slash variants.
    suffix = "/v1/chat/completions"
    if server_url.endswith(suffix):
        return server_url[: -len(suffix)] + "/v1/models"
    if server_url.endswith(suffix + "/"):
        return server_url[: -len(suffix) - 1] + "/v1/models"
    return ""


def _fallback_check(server_url: str, primary_error: str) -> dict:
    """Fall back to a lightweight POST against the chat completions endpoint.

    Args:
        server_url: The chat completions URL.
        primary_error: Error message from the primary check (empty if the
            primary check was skipped because the URL was not derivable).

    Returns:
        A ``check_server``-shaped result dict.
    """
    payload = {
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }
    try:
        resp = requests.post(server_url, json=payload, timeout=_HEALTH_TIMEOUT)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        reachable: bool = False
        if primary_error:
            error_msg = primary_error
        else:
            error_msg = f"Connection failed at {server_url}: {exc}"
        return {
            "reachable": False,
            "server_url": server_url,
            "models_endpoint_available": False,
            "reported_models": [],
            "error": error_msg,
        }

    # The server responded — it *is* reachable even if the status is not
    # 200 (a 4xx / 5xx still means the server is up).
    return {
        "reachable": True,
        "server_url": server_url,
        "models_endpoint_available": False,
        "reported_models": [],
        "error": "",
    }

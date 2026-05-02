"""Client for sending prompts to a llama-server OpenAI-compatible API.

Exposed API:
    run_prompt(config: dict, prompt: str) -> dict
"""

from __future__ import annotations

import time
from typing import Any

import requests

# Default request timeout in seconds.
_DEFAULT_TIMEOUT = 120


def run_prompt(config: dict, prompt: str) -> dict:
    """Send a prompt to llama-server and return the response with metadata.

    Uses the OpenAI-compatible chat completions endpoint configured in
    *config*.  Measures round-trip latency and extracts the model's reply
    text together with optional token-usage information.

    Args:
        config: Validated configuration dict (as returned by
            :func:`~runners.config_loader.load_config`).  Must contain
            ``config["runtime"]["server_url"]`` and the keys
            ``temperature``, ``top_p``, ``max_tokens`` under
            ``config["settings"]``.
        prompt: The user prompt text to send to the model.

    Returns:
        A dict with the following keys:

        - **response** (*str*): The model's reply content.
        - **latency_sec** (*float*): Round-trip wall-clock time in seconds,
          measured with ``time.perf_counter()``.
        - **usage** (*dict*): Token usage returned by the server, or an
          empty dict if the server did not provide usage data.
        - **raw_response** (*dict*): The full JSON response body from the
          server.

    Raises:
        ConnectionError: If the server is not reachable (connection
            refused, DNS failure, etc.).
        TimeoutError: If the server does not respond within the timeout
            window (default 120 seconds).
        RuntimeError: If the server returns a non-200 HTTP status code.
        KeyError: If the response JSON is missing expected fields
            (``choices[0].message.content``).
    """
    server_url: str = config["runtime"]["server_url"]
    temperature: float = config["settings"]["temperature"]
    top_p: float = config["settings"]["top_p"]
    max_tokens: int = config["settings"]["max_tokens"]

    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }

    start = time.perf_counter()

    try:
        resp = requests.post(
            server_url,
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
        )
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            f"Could not connect to llama-server at {server_url}: {exc}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise TimeoutError(
            f"Request to llama-server timed out after {_DEFAULT_TIMEOUT}s: {exc}"
        ) from exc

    latency_sec = time.perf_counter() - start

    if resp.status_code != 200:
        raise RuntimeError(
            f"llama-server returned HTTP {resp.status_code}: {resp.text}"
        )

    try:
        raw_response: dict[str, Any] = resp.json()
    except ValueError as exc:
        raise RuntimeError(
            f"llama-server returned non-JSON response: {resp.text[:200]}"
        ) from exc

    # Extract the model's reply text.
    try:
        response_text: str = raw_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise KeyError(
            f"Response JSON missing expected field 'choices[0].message.content': "
            f"available keys are {list(raw_response.keys())}"
        ) from exc

    # Token usage is optional — some servers may not return it.
    usage: dict[str, Any] = raw_response.get("usage", {})

    return {
        "response": response_text,
        "latency_sec": round(latency_sec, 3),
        "usage": usage,
        "raw_response": raw_response,
    }

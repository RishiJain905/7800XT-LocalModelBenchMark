"""Tests for runners.server_health — Task 05 Phase 2.

Covers all branches of ``check_server()``: reachable / unreachable servers,
valid and invalid /v1/models responses, connection errors, timeouts, and
the fallback path through the chat completions endpoint.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from runners.server_health import check_server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_config() -> dict:
    """Return a minimal valid config dict."""
    return {
        "id": "qwen-9b-q8-4k",
        "model_name": "Qwen3.5-9B",
        "runtime": {
            "server_url": "http://127.0.0.1:8080/v1/chat/completions",
        },
        "settings": {
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 1024,
        },
    }


def _mock_get_response(status_code: int = 200, json_data=None, text: str = ""):
    """Build a mock ``requests.get`` response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("Invalid JSON")
    return resp


def _mock_post_response(status_code: int = 200, json_data=None):
    """Build a mock ``requests.post`` response."""
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


# ---------------------------------------------------------------------------
# check_server
# ---------------------------------------------------------------------------


class TestCheckServer:
    """Server health checks against an OpenAI-compatible endpoint."""

    # -- Happy path ---------------------------------------------------------

    def test_reachable_with_models_endpoint(self):
        """/v1/models returns 200 + valid JSON with a ``data`` key."""
        config = _valid_config()
        mock_get = _mock_get_response(
            status_code=200,
            json_data={"data": [{"id": "local-model"}]},
        )

        with patch("runners.server_health.requests.get", return_value=mock_get):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["server_url"] == "http://127.0.0.1:8080/v1/chat/completions"
        assert result["models_endpoint_available"] is True
        assert result["reported_models"] == ["local-model"]
        assert result["error"] == ""

    def test_empty_reported_models(self):
        """/v1/models returns an empty ``data`` list."""
        config = _valid_config()
        mock_get = _mock_get_response(
            status_code=200,
            json_data={"data": []},
        )

        with patch("runners.server_health.requests.get", return_value=mock_get):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is True
        assert result["reported_models"] == []

    def test_multiple_reported_models(self):
        """/v1/models reports multiple models."""
        config = _valid_config()
        mock_get = _mock_get_response(
            status_code=200,
            json_data={"data": [{"id": "model-a"}, {"id": "model-b"}]},
        )

        with patch("runners.server_health.requests.get", return_value=mock_get):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["reported_models"] == ["model-a", "model-b"]

    # -- /v1/models non-200 status (server reachable, endpoint not) ---------

    def test_reachable_without_models_endpoint_404(self):
        """/v1/models returns 404 — server is reachable but no models endpoint."""
        config = _valid_config()
        mock_get = _mock_get_response(status_code=404)

        with patch("runners.server_health.requests.get", return_value=mock_get):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is False
        assert result["reported_models"] == []
        assert result["error"] == ""

    def test_reachable_models_500(self):
        """/v1/models returns 500 — server reachable, endpoint broken."""
        config = _valid_config()
        mock_get = _mock_get_response(status_code=500)

        with patch("runners.server_health.requests.get", return_value=mock_get):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is False

    # -- /v1/models non-JSON (server reachable, endpoint broken) ------------

    def test_non_json_response_from_models(self):
        """/v1/models returns 200 but body is not valid JSON."""
        config = _valid_config()
        mock_get = _mock_get_response(status_code=200)  # No json_data → ValueError

        with patch("runners.server_health.requests.get", return_value=mock_get):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is False
        assert result["reported_models"] == []
        assert result["error"] == ""

    def test_models_missing_data_key(self):
        """/v1/models returns 200 + valid JSON but no ``data`` key."""
        config = _valid_config()
        mock_get = _mock_get_response(
            status_code=200,
            json_data={"not_data": "something"},
        )

        with patch("runners.server_health.requests.get", return_value=mock_get):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is False

    # -- Connection refused -------------------------------------------------

    def test_connection_refused(self):
        """/v1/models raises ConnectionError, fallback POST also fails."""
        config = _valid_config()

        with patch(
            "runners.server_health.requests.get",
            side_effect=requests.exceptions.ConnectionError("Connection refused"),
        ):
            with patch(
                "runners.server_health.requests.post",
                side_effect=requests.exceptions.ConnectionError("Connection refused"),
            ):
                result = check_server(config)

        assert result["reachable"] is False
        assert "refused" in result["error"].lower()
        assert result["server_url"] == "http://127.0.0.1:8080/v1/chat/completions"
        assert result["models_endpoint_available"] is False

    # -- Timeout ------------------------------------------------------------

    def test_timeout(self):
        """/v1/models raises Timeout, fallback POST also fails."""
        config = _valid_config()

        with patch(
            "runners.server_health.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with patch(
                "runners.server_health.requests.post",
                side_effect=requests.exceptions.Timeout("timed out"),
            ):
                result = check_server(config)

        assert result["reachable"] is False
        assert (
            "timeout" in result["error"].lower()
            or "timed out" in result["error"].lower()
        )
        assert result["models_endpoint_available"] is False

    # -- Fallback to chat completions ---------------------------------------

    def test_fallback_to_chat_completions(self):
        """/v1/models fails with ConnectionError, but POST fallback succeeds."""
        config = _valid_config()
        mock_post = _mock_post_response(status_code=200)

        with patch(
            "runners.server_health.requests.get",
            side_effect=requests.exceptions.ConnectionError("Connection refused"),
        ):
            with patch("runners.server_health.requests.post", return_value=mock_post):
                result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is False
        assert result["reported_models"] == []
        assert result["error"] == ""

    def test_fallback_succeeds_after_timeout(self):
        """/v1/models times out, but POST fallback succeeds."""
        config = _valid_config()
        mock_post = _mock_post_response(status_code=200)

        with patch(
            "runners.server_health.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with patch("runners.server_health.requests.post", return_value=mock_post):
                result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is False
        assert result["error"] == ""

    # -- Missing config keys ------------------------------------------------

    def test_missing_server_url(self):
        """Config has ``runtime`` but no ``server_url`` key."""
        config = {"runtime": {}}

        result = check_server(config)

        assert result["reachable"] is False
        assert result["server_url"] == ""
        assert "server_url" in result["error"].lower()
        assert "missing" in result["error"].lower()

    def test_missing_runtime_key(self):
        """Config has no ``runtime`` key at all."""
        config = {"id": "test"}

        result = check_server(config)

        assert result["reachable"] is False
        assert result["server_url"] == ""
        assert "server_url" in result["error"].lower()

    def test_empty_config(self):
        """Config is an empty dict."""
        result = check_server({})

        assert result["reachable"] is False
        assert result["server_url"] == ""
        assert result["models_endpoint_available"] is False
        assert result["reported_models"] == []
        assert result["error"] != ""

    # -- URL derivation -----------------------------------------------------

    def test_derived_models_url(self):
        """Requests.get is called with the correct derived /v1/models URL."""
        config = _valid_config()
        mock_get = _mock_get_response(
            status_code=200,
            json_data={"data": [{"id": "x"}]},
        )

        with patch(
            "runners.server_health.requests.get", return_value=mock_get
        ) as mock_req:
            check_server(config)

        mock_req.assert_called_once()
        call_args = mock_req.call_args[0]
        assert call_args[0] == "http://127.0.0.1:8080/v1/models"

    def test_server_url_without_chat_completions_path(self):
        """server_url does NOT end with /v1/chat/completions — falls back."""
        config = {
            "runtime": {"server_url": "http://127.0.0.1:8080/api/custom"},
        }
        mock_post = _mock_post_response(status_code=200)

        with patch(
            "runners.server_health.requests.post", return_value=mock_post
        ) as mock_req:
            result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is False
        mock_req.assert_called_once()

    def test_server_url_trailing_slash_derivation(self):
        """server_url ends with /v1/chat/completions/ — still derives."""
        config = {
            "runtime": {"server_url": "http://127.0.0.1:8080/v1/chat/completions/"},
        }
        mock_get = _mock_get_response(
            status_code=200,
            json_data={"data": [{"id": "x"}]},
        )

        with patch(
            "runners.server_health.requests.get", return_value=mock_get
        ) as mock_req:
            check_server(config)

        mock_req.assert_called_once()
        call_args = mock_req.call_args[0]
        assert call_args[0] == "http://127.0.0.1:8080/v1/models"

    def test_server_url_empty_string(self):
        """server_url is an empty string."""
        config = {"runtime": {"server_url": ""}}

        result = check_server(config)

        assert result["reachable"] is False
        assert result["server_url"] == ""

    # -- Fallback POST also returns non-200 (still reachable) ---------------

    def test_fallback_post_returns_404_but_server_reachable(self):
        """Fallback POST returns 404 — server is still reachable."""
        config = {
            "runtime": {"server_url": "http://127.0.0.1:8080/api/custom"},
        }
        mock_post = _mock_post_response(status_code=404)

        with patch("runners.server_health.requests.post", return_value=mock_post):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is False

    # -- JSON with data key but malformed entries ---------------------------

    def test_models_data_entries_missing_id(self):
        """Entries in ``data`` list are missing the ``id`` key."""
        config = _valid_config()
        mock_get = _mock_get_response(
            status_code=200,
            json_data={"data": [{"name": "model"}, {}]},
        )

        with patch("runners.server_health.requests.get", return_value=mock_get):
            result = check_server(config)

        assert result["reachable"] is True
        assert result["models_endpoint_available"] is True
        assert result["reported_models"] == ["", ""]

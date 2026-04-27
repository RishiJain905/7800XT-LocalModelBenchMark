"""Tests for runners.config_loader — Task 02: Model Config Format."""

from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from runners.config_loader import load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(tmp_dir: str, filename: str, data: dict) -> str:
    """Write a YAML dict to a file in tmp_dir and return the full path."""
    path = os.path.join(tmp_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
    return path


def _valid_config() -> dict:
    """Return a minimal config dict that passes all validations."""
    return {
        "id": "qwen-9b-q8-4k",
        "model_name": "Qwen3.5-9B",
        "model_path": "D:/LOCAL-MODELS/Qwen3.5-9B-Q8.gguf",
        "runtime": {
            "engine": "llama.cpp",
            "server_url": "http://127.0.0.1:8080/v1/chat/completions",
        },
        "settings": {
            "context_size": 4096,
            "gpu_layers": 99,
            "flash_attn": True,
            "cache_type_k": "q8_0",
            "cache_type_v": "q8_0",
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 1024,
        },
        "hardware": {
            "gpu": "RX 7800 XT",
            "vram_gb": 16,
            "backend": "ROCm",
        },
    }


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestLoadConfigHappyPath:
    """load_config succeeds with a well-formed config."""

    def test_returns_dict_with_all_top_level_keys(self, tmp_path):
        path = _write_yaml(str(tmp_path), "valid.yaml", _valid_config())
        result = load_config(path)
        assert isinstance(result, dict)
        for key in ("id", "model_name", "runtime", "settings"):
            assert key in result

    def test_preserves_nested_values(self, tmp_path):
        path = _write_yaml(str(tmp_path), "valid.yaml", _valid_config())
        result = load_config(path)
        assert result["id"] == "qwen-9b-q8-4k"
        assert (
            result["runtime"]["server_url"]
            == "http://127.0.0.1:8080/v1/chat/completions"
        )
        assert result["settings"]["temperature"] == 0
        assert result["settings"]["top_p"] == 1
        assert result["settings"]["max_tokens"] == 1024

    def test_load_actual_config_file(self):
        """Load the real configs/qwen-9b-q8-4k.yaml shipped with the repo."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(repo_root, "configs", "qwen-9b-q8-4k.yaml")
        if not os.path.exists(config_path):
            pytest.skip("Shipped config file not yet present")
        result = load_config(config_path)
        assert result["id"] == "qwen-9b-q8-4k"


# ---------------------------------------------------------------------------
# Top-level required-key validation
# ---------------------------------------------------------------------------


class TestMissingTopLevelKeys:
    """Each missing top-level required key raises ValueError."""

    @pytest.mark.parametrize("missing_key", ["id", "model_name", "runtime", "settings"])
    def test_missing_top_level_key_raises(self, tmp_path, missing_key):
        data = _valid_config()
        del data[missing_key]
        path = _write_yaml(str(tmp_path), "bad.yaml", data)
        with pytest.raises(ValueError, match=missing_key):
            load_config(path)


# ---------------------------------------------------------------------------
# Nested required-key validation
# ---------------------------------------------------------------------------


class TestMissingNestedKeys:
    """Missing nested required keys raise ValueError."""

    def test_missing_runtime_server_url(self, tmp_path):
        data = _valid_config()
        del data["runtime"]["server_url"]
        path = _write_yaml(str(tmp_path), "bad.yaml", data)
        with pytest.raises(ValueError, match="server_url"):
            load_config(path)

    def test_missing_settings_temperature(self, tmp_path):
        data = _valid_config()
        del data["settings"]["temperature"]
        path = _write_yaml(str(tmp_path), "bad.yaml", data)
        with pytest.raises(ValueError, match="temperature"):
            load_config(path)

    def test_missing_settings_top_p(self, tmp_path):
        data = _valid_config()
        del data["settings"]["top_p"]
        path = _write_yaml(str(tmp_path), "bad.yaml", data)
        with pytest.raises(ValueError, match="top_p"):
            load_config(path)

    def test_missing_settings_max_tokens(self, tmp_path):
        data = _valid_config()
        del data["settings"]["max_tokens"]
        path = _write_yaml(str(tmp_path), "bad.yaml", data)
        with pytest.raises(ValueError, match="max_tokens"):
            load_config(path)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """File-not-found and non-dict YAML produce clear errors."""

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_non_dict_yaml_raises(self, tmp_path):
        """A YAML file that parses to a list (not dict) should raise."""
        path = os.path.join(str(tmp_path), "list.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write("- item1\n- item2\n")
        with pytest.raises(ValueError, match="dict"):
            load_config(path)

    def test_empty_file_raises(self, tmp_path):
        path = os.path.join(str(tmp_path), "empty.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        with pytest.raises(ValueError, match="dict"):
            load_config(path)

# -*- coding: utf-8 -*-
"""Tests for the model registry."""

from __future__ import annotations

import os

import pytest
import yaml

from runners.config_loader import load_config
from runners.model_registry import (
    clear_cache,
    get_model_config,
    list_model_configs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_model_config(model_id="test-model", model_name="Test Model"):
    return {
        "id": model_id,
        "model_name": model_name,
        "runtime": {"server_url": "http://localhost:8080/v1/chat/completions"},
        "settings": {
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 1024,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_model_configs():
    """Return a list of valid model config dicts."""
    return [
        _valid_model_config(model_id="model-a", model_name="Model A"),
        _valid_model_config(model_id="model-b", model_name="Model B"),
    ]


@pytest.fixture
def setup_model_env(tmp_path, valid_model_configs):
    """Set up a temporary project root with configs/models/*.yaml."""
    models_dir = tmp_path / "configs" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    for config in valid_model_configs:
        config_path = models_dir / f"{config['id']}.yaml"
        with open(str(config_path), "w", encoding="utf-8") as f:
            yaml.dump(config, f)
    return tmp_path


# ---------------------------------------------------------------------------
# Tests: list_model_configs
# ---------------------------------------------------------------------------


class TestListModelConfigs:
    """Tests for list_model_configs()."""

    def test_lists_all_configs(self, setup_model_env, valid_model_configs):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_model_env))
            clear_cache()
            configs = list_model_configs()
            assert len(configs) == len(valid_model_configs)
            ids = {c["id"] for c in configs}
            for config in valid_model_configs:
                assert config["id"] in ids
        finally:
            os.chdir(cwd)

    def test_each_config_has_id_and_model_name(self, setup_model_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_model_env))
            clear_cache()
            configs = list_model_configs()
            for config in configs:
                assert "id" in config
                assert "model_name" in config
        finally:
            os.chdir(cwd)

    def test_empty_models_dir_returns_empty_list(self, tmp_path):
        cwd = os.getcwd()
        try:
            empty_dir = tmp_path / "configs" / "models"
            empty_dir.mkdir(parents=True, exist_ok=True)
            os.chdir(str(tmp_path))
            clear_cache()
            configs = list_model_configs()
            assert configs == []
        finally:
            os.chdir(cwd)

    def test_cached_list_returns_same_data(self, setup_model_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_model_env))
            clear_cache()
            configs1 = list_model_configs()
            configs2 = list_model_configs()
            assert configs1 == configs2
        finally:
            os.chdir(cwd)

    def test_list_returns_deep_copy(self, setup_model_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_model_env))
            clear_cache()
            configs1 = list_model_configs()
            configs2 = list_model_configs()
            configs1.append({"id": "extra.model"})
            assert len(configs1) == len(configs2) + 1
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# Tests: get_model_config
# ---------------------------------------------------------------------------


class TestGetModelConfig:
    """Tests for get_model_config()."""

    def test_get_existing_config(self, setup_model_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_model_env))
            clear_cache()
            config = get_model_config("model-a")
            assert config["id"] == "model-a"
            assert config["model_name"] == "Model A"
            assert (
                config["runtime"]["server_url"]
                == "http://localhost:8080/v1/chat/completions"
            )
            assert config["settings"]["temperature"] == 0
            assert config["settings"]["top_p"] == 1
            assert config["settings"]["max_tokens"] == 1024
        finally:
            os.chdir(cwd)

    def test_get_nonexistent_config(self, setup_model_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_model_env))
            clear_cache()
            with pytest.raises(KeyError, match="not found"):
                get_model_config("nonexistent.model")
        finally:
            os.chdir(cwd)

    def test_get_returns_copy(self, setup_model_env):
        cwd = os.getcwd()
        try:
            os.chdir(str(setup_model_env))
            clear_cache()
            config = get_model_config("model-a")
            config["model_name"] = "Modified"
            config2 = get_model_config("model-a")
            assert config2["model_name"] == "Model A"
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# Tests: validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    """Tests for error handling in model registry."""

    def test_duplicate_config_ids(self, tmp_path):
        cwd = os.getcwd()
        try:
            models_dir = tmp_path / "configs" / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            base = _valid_model_config(model_id="duplicate-id", model_name="Duplicate")
            for name in ("first.yaml", "second.yaml"):
                path = models_dir / name
                with open(str(path), "w", encoding="utf-8") as f:
                    yaml.dump(base, f)
            os.chdir(str(tmp_path))
            clear_cache()
            with pytest.raises(ValueError, match="duplicate"):
                list_model_configs()
        finally:
            os.chdir(cwd)

    def test_invalid_yaml_file(self, tmp_path):
        cwd = os.getcwd()
        try:
            models_dir = tmp_path / "configs" / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            bad_file = models_dir / "invalid.yaml"
            # YAML that parses to a list (not dict) — load_config raises ValueError
            bad_file.write_text("- item1\n- item2\n", encoding="utf-8")
            os.chdir(str(tmp_path))
            clear_cache()
            with pytest.raises(ValueError, match="dict"):
                list_model_configs()
        finally:
            os.chdir(cwd)

    def test_config_missing_required_field(self, tmp_path):
        cwd = os.getcwd()
        try:
            models_dir = tmp_path / "configs" / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            config = _valid_model_config()
            del config["id"]
            path = models_dir / "missing_id.yaml"
            with open(str(path), "w", encoding="utf-8") as f:
                yaml.dump(config, f)
            os.chdir(str(tmp_path))
            clear_cache()
            with pytest.raises(ValueError, match="id"):
                list_model_configs()
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# Tests: backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Integration tests ensuring load_config remains usable directly."""

    def test_direct_path_still_loads(self, tmp_path):
        """Loading a config outside configs/models/ via direct path works."""
        config = _valid_model_config(model_id="standalone", model_name="Standalone")
        path = tmp_path / "standalone.yaml"
        with open(str(path), "w", encoding="utf-8") as f:
            yaml.dump(config, f)
        result = load_config(str(path))
        assert result["id"] == "standalone"

    def test_original_config_path_still_loads(self):
        """Load the real configs/qwen-9b-q8-4k.yaml shipped with the repo."""
        repo_root = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(repo_root, "configs", "qwen-9b-q8-4k.yaml")
        if not os.path.exists(config_path):
            pytest.skip("Shipped config file not yet present")
        result = load_config(config_path)
        assert result["id"] == "qwen-9b-q8-4k"

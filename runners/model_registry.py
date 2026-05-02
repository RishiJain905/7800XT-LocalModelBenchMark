# -*- coding: utf-8 -*-
"""Model registry — discovers and describes available model configurations."""

from __future__ import annotations

import copy
import glob
import os.path
from typing import Any

from .config_loader import load_config

_MODELS_DIR = "configs/models"

# Internal cache populated on first call
_models_cache: list[dict[str, Any]] | None = None


def _resolve_path(path: str) -> str:
    """Resolve a relative path against the project root."""
    return os.path.normpath(path)


def _scan_and_load() -> list[dict[str, Any]]:
    """Scan configs/models/*.yaml and load each via load_config().

    Returns the list of validated config dicts.  If the directory does not
    exist, returns an empty list (no FileNotFoundError).

    Raises ValueError if duplicate IDs are found across the scanned files.
    """
    path = _resolve_path(_MODELS_DIR)

    if not os.path.isdir(path):
        return []

    yaml_files = sorted(
        f for f in glob.glob(os.path.join(path, "*.yaml")) if os.path.isfile(f)
    )

    configs: list[dict[str, Any]] = []
    for yf in yaml_files:
        configs.append(load_config(yf))

    # Validate no duplicate IDs
    seen_ids: set[str] = set()
    for cfg in configs:
        mid: str = cfg["id"]
        if mid in seen_ids:
            raise ValueError(f"Duplicate model config id: {mid}.")
        seen_ids.add(mid)

    return configs


def list_model_configs() -> list[dict[str, Any]]:
    """Return all available model configs from configs/models/.

    Each dict is a deep copy of the full validated config.

    Raises FileNotFoundError or ValueError on invalid registry state.
    """
    global _models_cache
    if _models_cache is None:
        _models_cache = _scan_and_load()
    return copy.deepcopy(_models_cache)


def get_model_config(model_id: str) -> dict[str, Any]:
    """Return a single model config by its id field.

    Raises KeyError if the model_id is not found.
    Raises FileNotFoundError or ValueError on invalid registry state.
    """
    configs = list_model_configs()
    for cfg in configs:
        if cfg["id"] == model_id:
            return dict(cfg)
    raise KeyError(
        f"Model config not found: '{model_id}'. "
        f"Available configs: {[c['id'] for c in configs]}."
    )


def clear_cache() -> None:
    """Clear the internal model config cache. Used in testing."""
    global _models_cache
    _models_cache = None

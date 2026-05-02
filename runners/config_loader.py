"""Load and validate model configuration from YAML files.

Exposed API:
    load_config(path: str) -> dict
"""

from __future__ import annotations

from pathlib import Path

import yaml

# Required top-level keys in every model config.
_REQUIRED_TOP_KEYS = {"id", "model_name", "runtime", "settings"}

# Required nested keys: (parent_key, required_child_key)
_REQUIRED_NESTED_KEYS = [
    ("runtime", "server_url"),
    ("settings", "temperature"),
    ("settings", "top_p"),
    ("settings", "max_tokens"),
]


def load_config(path: str) -> dict:
    """Load a YAML config file and validate required fields.

    Args:
        path: Filesystem path to the YAML config file.

    Returns:
        Validated config as a plain dict.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file does not parse to a dict or is missing
            required keys.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"Config file must contain a YAML mapping (dict), got {type(data).__name__}"
        )

    # Validate top-level keys.
    missing_top = _REQUIRED_TOP_KEYS - set(data.keys())
    if missing_top:
        raise ValueError(
            f"Missing required top-level key(s): {', '.join(sorted(missing_top))}"
        )

    # Validate nested keys.
    for parent, child in _REQUIRED_NESTED_KEYS:
        section = data.get(parent, {})
        if not isinstance(section, dict) or child not in section:
            raise ValueError(f"Missing required key '{child}' in '{parent}'")

    return data

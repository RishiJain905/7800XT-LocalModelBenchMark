"""Task loader for loading and parsing task definitions from JSONL files."""

import json
from pathlib import Path
from typing import List, Dict, Any

from .validators import validate_task, ValidationError


def load_tasks(path: str) -> List[Dict[str, Any]]:
    """
    Load tasks from a JSONL file.

    Args:
        path: Path to the JSONL file containing tasks

    Returns:
        List of validated task dictionaries

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file contains invalid JSON, malformed data,
            or tasks that fail validation
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Task file not found: {path}")

    if not path_obj.is_file():
        raise ValueError(f"Path is not a file: {path}")

    tasks = []
    line_number = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_number += 1
            line = line.strip()

            # Skip blank lines
            if not line:
                continue

            try:
                task = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_number}: {e.msg}") from e

            if not isinstance(task, dict):
                raise ValueError(
                    f"Line {line_number}: Expected JSON object, got {type(task).__name__}"
                )

            try:
                validate_task(task)
            except ValidationError as e:
                raise ValueError(f"Line {line_number}: {e.message}") from e

            tasks.append(task)

    return tasks

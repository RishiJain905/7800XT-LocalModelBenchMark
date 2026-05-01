"""Exact match scorer — compares normalized expected vs actual strings."""

from __future__ import annotations


def score(task: dict, response: str) -> dict:
    """Score a response by exact string match against task["expected"].

    Normalizes both strings by stripping whitespace and lowercasing before
    comparison.

    Args:
        task: Task dictionary containing an ``expected`` key with the reference
            answer.
        response: The model's raw text response.

    Returns:
        A dict with ``score`` (0.0 or 1.0), ``passed`` (bool), and
        ``reason`` (str).
    """
    if response is None:
        return {
            "score": 0.0,
            "passed": False,
            "reason": "Response is None",
        }

    if not isinstance(response, str):
        response = str(response)

    if "expected" not in task:
        return {
            "score": 0.0,
            "passed": False,
            "reason": "Task is missing 'expected' key",
        }

    expected_raw = task["expected"]
    if expected_raw is None:
        return {
            "score": 0.0,
            "passed": False,
            "reason": "Task 'expected' value is None",
        }

    if not isinstance(expected_raw, str):
        expected_raw = str(expected_raw)

    normalized_expected = expected_raw.strip().lower()
    normalized_response = response.strip().lower()

    if normalized_expected == normalized_response:
        return {
            "score": 1.0,
            "passed": True,
            "reason": "Matched expected answer",
        }

    return {
        "score": 0.0,
        "passed": False,
        "reason": (f"Expected '{expected_raw.strip()}' but got '{response.strip()}'"),
    }

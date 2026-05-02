"""Numeric closeness scorer — compares extracted number against expected value."""

from __future__ import annotations

import re


# Match integers, decimals, and negative numbers.
# Will NOT match NaN, Inf, or hex.
_NUMBER_RE = re.compile(r"-?(?:\d+\.?\d*|\.\d+)")


def score(task: dict, response: str) -> dict:
    """Score a response by extracting a number and comparing to task["expected"].

    Extracts the first numeric value found in *response* and checks whether
    it falls within the configured tolerance of *task["expected"]*.

    Args:
        task: Task dictionary containing ``expected`` (numeric value) and
            optionally ``tolerance`` (default 0.01).
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

    # --- Validate / extract expected value ---------------------------------
    expected_key = "expected" if "expected" in task else "expected_output"
    if expected_key not in task:
        return {
            "score": 0.0,
            "passed": False,
            "reason": "Task is missing 'expected' key",
        }

    expected_raw = task[expected_key]
    try:
        expected = float(expected_raw)
    except (TypeError, ValueError):
        return {
            "score": 0.0,
            "passed": False,
            "reason": f"Task 'expected' is not numeric: {expected_raw!r}",
        }

    # --- Extract first number from response --------------------------------
    match = _NUMBER_RE.search(response)
    if match is None:
        return {
            "score": 0.0,
            "passed": False,
            "reason": f"No number found in response: '{response.strip()}'",
        }

    try:
        actual = float(match.group())
    except ValueError:
        return {
            "score": 0.0,
            "passed": False,
            "reason": f"Could not parse number from response: '{response.strip()}'",
        }

    # --- Compare with tolerance --------------------------------------------
    tolerance = task.get("tolerance", 0.01)

    if abs(actual - expected) <= tolerance:
        return {
            "score": 1.0,
            "passed": True,
            "reason": (
                f"Value {actual} within tolerance {tolerance} of expected {expected}"
            ),
        }

    return {
        "score": 0.0,
        "passed": False,
        "reason": (f"Expected {expected} (±{tolerance}) but got {actual}"),
    }

"""JSON validity scorer — validates structure and required keys in JSON responses."""

from __future__ import annotations

import json
from typing import Any


def score(task: dict, response: str) -> dict:
    """Score a response by parsing it as JSON and optionally checking structure.

    Checks performed (in order):
    1. Response parses as valid JSON.
    2. If ``task["expected_tool"]`` is present, ``parsed["tool"]`` must match
       exactly.
    3. If ``task["required_argument_keys"]`` is present, each listed key must
       exist in ``parsed["arguments"]``.

    The overall score is the fraction of applicable checks that pass.

    Args:
        task: Task dictionary optionally containing ``expected_tool`` and
            ``required_argument_keys``.
        response: The model's raw text response.

    Returns:
        A dict with ``score`` (0.0–1.0), ``passed`` (bool), and
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

    # --- 1. Parse JSON -----------------------------------------------------
    stripped = response.strip()
    try:
        parsed: Any = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return {
            "score": 0.0,
            "passed": False,
            "reason": f"Invalid JSON: {exc}",
        }

    # parsed must be a dict for the rest of the checks to make sense
    if not isinstance(parsed, dict):
        return {
            "score": 0.0,
            "passed": False,
            "reason": f"JSON parsed but result is {type(parsed).__name__}, expected object",
        }

    # --- Determine which checks apply and run them -------------------------
    checks_total = 1  # JSON parse always counts as 1
    checks_passed = 1 if isinstance(parsed, dict) else 0
    reasons: list[str] = ["JSON parsed successfully"]

    # 2. tool matching
    metadata = task.get("metadata", {})
    expected_tool = task.get("expected_tool", metadata.get("expected_tool"))
    required_keys = task.get(
        "required_argument_keys", metadata.get("required_argument_keys")
    )

    if expected_tool is not None:
        checks_total += 1

        if "tool" not in parsed:
            reasons.append(f"Missing 'tool' key (expected '{expected_tool}')")
        elif parsed["tool"] != expected_tool:
            reasons.append(
                f"Tool mismatch: expected '{expected_tool}', got '{parsed['tool']}'"
            )
        else:
            checks_passed += 1
            reasons.append(f"Tool matches: '{expected_tool}'")

    # 3. required argument keys
    if required_keys is not None:
        checks_total += 1

        if not isinstance(required_keys, list):
            reasons.append(
                f"'required_argument_keys' is not a list: {type(required_keys).__name__}"
            )
        else:
            arguments = parsed.get("arguments")

            if arguments is None:
                reasons.append("Missing 'arguments' key in response")
            elif not isinstance(arguments, dict):
                reasons.append(
                    f"'arguments' is not an object: {type(arguments).__name__}"
                )
            else:
                missing_keys = [k for k in required_keys if k not in arguments]
                if missing_keys:
                    reasons.append(f"Missing argument keys: {', '.join(missing_keys)}")
                else:
                    checks_passed += 1
                    reasons.append(
                        f"All required argument keys present: {', '.join(required_keys)}"
                    )

    # --- Compute final score -----------------------------------------------
    score_value = checks_passed / checks_total if checks_total > 0 else 0.0
    # Pass if *all* applicable checks passed
    passed = checks_passed == checks_total

    return {
        "score": round(score_value, 4),
        "passed": passed,
        "reason": "; ".join(reasons),
    }

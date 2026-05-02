"""Keyword match scorer — checks presence of expected keywords in response."""

from __future__ import annotations


def score(task: dict, response: str) -> dict:
    """Score a response by checking for expected keywords.

    Reads ``task["expected_keywords"]`` (list of strings) and counts how
    many appear (case-insensitive) in *response*.  The score is the ratio
    of matched keywords to total keywords.

    Args:
        task: Task dictionary containing ``expected_keywords`` and
            optionally ``threshold`` (default 0.7).
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

    # --- Handle missing / empty expected_keywords --------------------------
    keywords = task.get("expected_keywords")
    if keywords is None:
        keywords = task.get("metadata", {}).get("keywords")

    if keywords is None:
        return {
            "score": 0.0,
            "passed": False,
            "reason": "Task is missing 'expected_keywords' or 'metadata.keywords' key",
        }

    if not isinstance(keywords, list):
        return {
            "score": 0.0,
            "passed": False,
            "reason": f"Task keywords ('expected_keywords' or 'metadata.keywords') is not a list: {type(keywords).__name__}",
        }

    # An empty keyword list trivially passes.
    if len(keywords) == 0:
        return {
            "score": 1.0,
            "passed": True,
            "reason": "No keywords required",
        }

    # --- Case-insensitive keyword matching ---------------------------------
    response_lower = response.lower()
    matched = []
    unmatched = []

    for keyword in keywords:
        keyword_str = str(keyword).lower()
        if keyword_str in response_lower:
            matched.append(str(keyword))
        else:
            unmatched.append(str(keyword))

    score_value = len(matched) / len(keywords)
    threshold = task.get("threshold", task.get("metadata", {}).get("threshold", 0.7))
    passed = score_value >= threshold

    if passed:
        return {
            "score": score_value,
            "passed": True,
            "reason": (
                f"Matched {len(matched)}/{len(keywords)} keywords "
                f"(threshold={threshold})"
            ),
        }

    return {
        "score": score_value,
        "passed": False,
        "reason": (
            f"Matched {len(matched)}/{len(keywords)} keywords "
            f"(threshold={threshold}); missing: {', '.join(unmatched)}"
        ),
    }

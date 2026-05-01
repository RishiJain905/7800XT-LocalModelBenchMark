"""Scorer registry — maps scorer names to their score functions."""

from __future__ import annotations

from scorers.exact_match import score as exact_match_score
from scorers.json_valid import score as json_valid_score
from scorers.keyword_match import score as keyword_match_score
from scorers.numeric_close import score as numeric_close_score

_REGISTRY: dict[str, callable] = {
    "exact_match": exact_match_score,
    "numeric_close": numeric_close_score,
    "keyword_match": keyword_match_score,
    "json_valid": json_valid_score,
}

_SUPPORTED = sorted(_REGISTRY.keys())


def get_scorer(name: str) -> callable:
    """Return the scorer function registered under *name*.

    Args:
        name: One of ``"exact_match"``, ``"numeric_close"``,
            ``"keyword_match"``, or ``"json_valid"``.

    Returns:
        The ``score(task, response) -> dict`` callable.

    Raises:
        ValueError: If *name* is not a registered scorer.
    """
    scorer = _REGISTRY.get(name)
    if scorer is None:
        raise ValueError(
            f"Unknown scorer: {name!r}. Supported: {', '.join(_SUPPORTED)}"
        )
    return scorer

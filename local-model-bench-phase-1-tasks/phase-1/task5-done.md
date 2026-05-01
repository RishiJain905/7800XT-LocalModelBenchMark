# Task 05 — Build Basic Scorers ✅ DONE

## Status

**Completed** — All 4 scorer modules and registry implemented, 79 tests passing.

## What Was Delivered

- **Files created**: `scorers/exact_match.py`, `scorers/numeric_close.py`, `scorers/keyword_match.py`, `scorers/json_valid.py`, `scorers/registry.py`
- **Package updated**: `scorers/__init__.py` exports `get_scorer`
- **Tests created**: `tests/test_scorers.py` (79 tests, all passing)

## Implementation Summary

| Requirement | Implementation |
|---|---|
| Common return format | Every scorer returns `{"score": float, "passed": bool, "reason": str}` |
| `exact_match` scorer | Normalizes via strip + lowercase; handles missing `expected` and None response |
| `numeric_close` scorer | Regex extracts first number; default tolerance 0.01; configurable via `task["tolerance"]` |
| `keyword_match` scorer | Case-insensitive keyword counting; `score = matched / total`; default threshold 0.7; configurable via `task["threshold"]` |
| `json_valid` scorer | Parses JSON; checks `expected_tool` and `required_argument_keys` if present; partial credit on partial matches |
| `registry.py` | `get_scorer(name)` returns scorer function; raises `ValueError` for unknown names |
| Graceful bad input | All scorers handle missing keys, wrong types, empty input without raising exceptions |
| No external dependencies | Uses only `re`, `json`, `typing` from stdlib |

## Test Results

```
79 passed in 0.06s
```

| Test Class | Tests | Coverage |
|---|---|---|
| `TestExactMatchScore` | 13 | Exact match, case/whitespace normalization, missing keys, empty input, non-string coercion |
| `TestNumericCloseScore` | 16 | Exact match, tolerance boundaries, custom tolerance, text extraction, missing/non-numeric expected, negatives |
| `TestKeywordMatchScore` | 10 | Full/partial/no match, default/custom thresholds, case insensitivity, empty keywords, missing key |
| `TestJsonValidScore` | 16 | Valid JSON, tool matching, argument keys, partial credit, malformed input, non-dict JSON, whitespace |
| `TestRegistry` | 7 | All 4 scorers by name, callable check, ValueError on unknown, message content, empty/None name |

## Done Criteria Met

- ✅ All four scorer files exist
- ✅ `scorers/registry.py` exists
- ✅ Each scorer returns the common scoring format
- ✅ Each scorer handles bad input gracefully
- ✅ Unknown scorer names raise clear `ValueError`

## Notes

- Style consistent with existing codebase (docstrings, type hints, PEP 8)
- No new dependencies added (stdlib only)
- All scorers are deterministic and lightweight, ready for extension in later phases

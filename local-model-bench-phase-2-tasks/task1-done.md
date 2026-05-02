# Task 01 — Freeze Phase 1 Contract ✅

## Deliverables

### Contract Document
- **Created:** `docs/phase-1-contract.md`
- **Sections:** All 8 required sections:
  1. Valid model config fields
  2. Valid JSONL task fields
  3. Category-to-scorer behavior
  4. Batch CLI arguments
  5. Raw result object shape
  6. Summary CSV columns
  7. Leaderboard behavior
  8. Backward-compatibility expectations

### Tests Added (12 new tests)

**`tests/test_run_benchmark.py`:**
| Test | Purpose |
|------|---------|
| `test_dry_run_contract` | `--dry-run` still works without API calls |
| `test_summary_csv_header_contract` | CSV header matches documented Phase 1 columns |
| `test_summary_csv_can_be_read_by_generate_leaderboard` | Leaderboard can consume Phase 1 format CSV |

**`tests/test_scorers.py`:**
| Test | Purpose |
|------|---------|
| `test_scorer_exact_match_contract_pass/fail` | `exact_match` accepts Phase 1 format |
| `test_scorer_numeric_close_contract_pass/fail/with_tolerance` | `numeric_close` accepts Phase 1 format with metadata tolerance |
| `test_scorer_keyword_match_contract_pass/fail/with_threshold` | `keyword_match` accepts Phase 1 format with metadata threshold |
| `test_scorer_json_valid_contract_pass/fail` | `json_valid` accepts Phase 1 format |

### Bug Fixes Found During Testing

| File | Fix |
|------|-----|
| `scorers/numeric_close.py` | Added `metadata.tolerance` fallback (was only reading top-level `tolerance`) |
| `scorers/keyword_match.py` | Added `metadata.threshold` fallback (was only reading top-level `threshold`) |

## Verification

```
python -m pytest tests/ -q
274 passed in 0.56s
```

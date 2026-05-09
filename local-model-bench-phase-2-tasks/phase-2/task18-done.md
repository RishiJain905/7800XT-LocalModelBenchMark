# Task 18 - Add Results Browser — Done

## Summary

Enhanced the results browser in `bench_tui.py` to show richer detail and group runs by model.

## Changes made

### `bench_tui.py` — `ResultsBrowserScreen`

- **Richer detail pane** (`_show_record`): Now displays server URL, settings, average latency, artifact count, artifact folder path, and started time alongside existing fields.
- **Model grouping**: Runs are now sorted by model config ID (ascending) then by started time (descending) within each group. Model header rows are inserted as visual separators.
- **Graceful fallbacks**: Missing/corrupt summary files fall back to empty dict; missing task_file falls back to manifest value; missing artifacts folder shows a clear "no artifacts folder" message.

### `tests/test_bench_tui.py` — New tests

Added 6 new tests:

| Test | What it covers |
|------|----------------|
| `test_discover_result_runs_handles_corrupted_manifest` | Unparseable manifest JSON is skipped |
| `test_discover_result_runs_empty_directory` | Empty/nonexistent runs dir returns `[]` |
| `test_discover_result_runs_missing_summary` | No summary.json returns empty dict fallback |
| `test_discover_result_runs_empty_summary_file` | Zero-byte summary.json returns empty dict fallback |
| `test_discover_result_runs_corrupted_summary_file` | Invalid JSON summary returns empty dict fallback |
| `test_discover_result_runs_multi_model_grouping` | Runs under different model dirs are all discovered |
| `test_show_record_detail_includes_latency_and_artifacts` | Detail output contains latency, artifact count, settings, and artifact path |

## Verification

```powershell
python -m pytest tests/test_bench_tui.py -q
```

Result: **21 passed** (15 existing + 6 new).

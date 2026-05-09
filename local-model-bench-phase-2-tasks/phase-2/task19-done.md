# Task 19 - Update README and User Docs — Done

## Summary

Updated the main README with missing Phase 2 documentation and created three new
user-facing docs files.

## Changes made

### `README.md` — Updated

- **CLI argument reference**: Added table of all CLI flags (`--config`, `--task-file`,
  `--suite`, `--resume`, `--dry-run`, `--repeats`) with descriptions.
- **Suite-based run**: Added `--suite` example alongside existing `--task-file` examples.
- **Resume docs**: Added `--resume` CLI usage with explanation of how it preserves
  completed attempts and only re-runs missing ones. Also noted the TUI resume flow
  (Results Browser > press `r`).
- **Importing Official Benchmarks**: New section covering all four supported sources
  (GSM8K, MMLU, MBPP, HumanEval) with import commands, options table, and dataset
  licensing notes.
- **Known Limitations**: New section documenting coding scoring limitations, server
  management, no web dashboard, no distributed execution, and single-server focus.
- **Project structure**: Updated to reflect all Phase 2 runners, scripts, benchmarks,
  and docs directories.

### `docs/model_configs.md` — Created

- File location and naming conventions
- Required and optional fields with complete tables
- Full example config
- Step-by-step guide for creating a new config
- Config validation behavior table (field errors, duplicate IDs)
- Backward compatibility with Phase 1 flat config paths
- Notes on mapping configs to `llama-server` instances

### `docs/benchmark_suites.md` — Created

- Complete table of all 8 built-in suites (ID, name, category, description, scoring)
- How to run via CLI and TUI
- Suite registry YAML format reference
- How to add a new suite (create JSONL + register in suites.yaml)
- Task file format reference with optional metadata field table
- Official benchmark import section

### `docs/tui_usage.md` — Created

- Screen-by-screen walkthrough (Dashboard, Model Selection, Suite Selection,
  Run Settings, Health Check, Run Progress, Results Browser)
- Full keyboard reference table covering all screens
- Cancellation behavior and background run notes
- Results browser detail pane fields
- Resume flow and prerequisites
- Troubleshooting table for common issues

## Verification

```powershell
python -m pytest tests/ -q
```

Result: **417 passed** (no regression from documentation changes).

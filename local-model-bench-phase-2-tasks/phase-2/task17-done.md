# Task 17 Done - Keyboard Terminal UI

Completed: 2026-05-06

## Summary

- Added `bench_tui.py` as a Textual-based keyboard terminal UI.
- Added dashboard, model selection, suite selection, run settings, live progress, and results browser screens.
- Added `python bench_tui.py --smoke-test` for CI/local validation without requiring `llama-server`.
- Wired TUI runs through existing registries, health checks, runner, result writer, resume helpers, and leaderboard generation.
- Added multi-suite execution with one structured run folder per suite.
- Added cancellation support through the runner `cancel_callback`, preserving completed attempts and writing cancelled metadata.
- Added results discovery and resume entry points for incomplete run folders.
- Added `textual>=8.2.3,<9` to `requirements.txt`.
- Added Task 17 TUI tests in `tests/test_bench_tui.py`.
- Updated `README.md` with TUI usage, keyboard controls, smoke-test command, structured run output, and manual validation notes.

## Verification

```powershell
python -m pytest tests/ -q
# 410 passed in 2.69s
```

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite reasoning.math --dry-run
# Config: qwen-9b-q8-4k
# Tasks: 20
# Suite: reasoning.math (Math)
```

```powershell
python bench_tui.py --smoke-test
# TUI smoke test passed
```

## Manual Notes

- Real benchmark validation still requires an already-running OpenAI-compatible local server.
- README now documents the manual TUI validation flow: launch `python bench_tui.py`, select the matching model config, check health, select a short suite, run with repeats `1`, observe progress, cancel once, confirm preserved `raw.jsonl`, and resume from the results browser.

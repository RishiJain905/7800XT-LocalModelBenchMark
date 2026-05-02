# [HARD] Task 17 - Build Keyboard Terminal UI

## Goal

Create a keyboard-driven terminal interface for running local benchmarks.

## Required entry point

Create:

```text
bench_tui.py
```

## Recommended dependency

Use `textual` if the app needs multiple panels, keyboard navigation, and a polished terminal UI.

If implementation risk is too high, use `rich` first only if it still supports fast keyboard/menu workflows.

## Required screens

Include:

- Dashboard.
- Model selection.
- Benchmark suite selection.
- Run settings.
- Live run progress.
- Results browser.

## Required behavior

- Navigate with keyboard.
- Show selected model config.
- Show server health status.
- Show available suites.
- Allow selecting one or more suites.
- Allow starting a run.
- Show progress, current task, score, and latency.
- Allow cancellation.

## Smoke test mode

Support:

```powershell
python bench_tui.py --smoke-test
```

This should validate that the app imports, registries load, and core screens can initialize without requiring `llama-server`.

## Done criteria

- TUI launches.
- User can complete a benchmark run from the TUI.
- TUI does not break the batch CLI.
- Smoke test can run in CI/local tests.
- Manual test notes are added to README.


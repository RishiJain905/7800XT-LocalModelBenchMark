# Phase 2 - End-to-End Local Model Benchmark Product

## Objective

Turn the Phase 1 benchmark harness into an end-to-end local model benchmarking product for already-running OpenAI-compatible local servers, especially `llama-server`.

Phase 2 should let a user select the model config currently loaded in `llama-server`, choose benchmark suites from a keyboard-driven terminal UI, run the benchmark, preserve all raw/model outputs, and compare runs across local models.

## Product target

At the end of Phase 2, this should be usable for testing real fine-tuned local models without editing code between runs.

The main workflow should be:

```powershell
python bench_tui.py
```

Expected user flow:

1. Select the model config that is currently loaded in `llama-server`.
2. Confirm the configured OpenAI-compatible endpoint is reachable.
3. Choose one or more benchmark suites.
4. Choose run settings such as repeats, max tasks, and resume behavior.
5. Run the benchmark from a keyboard-driven terminal interface.
6. Watch progress live.
7. Inspect saved outputs and summaries under a model/run-specific folder.
8. Compare results in generated summaries and leaderboards.

The existing non-interactive CLI should remain available:

```powershell
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file benchmarks/reasoning/math.jsonl
```

## Scope

### Included

- Reusable benchmark runner extracted from the current CLI.
- Model registry for any local OpenAI-compatible model config.
- Benchmark suite registry with categories such as coding, math, real-world reasoning, tool calling, instruction following, and long-context.
- Keyboard-driven terminal UI.
- Server health checks.
- Per-model run folders.
- Run manifests.
- Interrupt-safe writes.
- Resume support.
- Separate saved files for coding/model artifacts.
- Updated summaries and leaderboards.
- Initial official/open-source benchmark import path where practical.
- Strong tests for core behavior.
- README updates so the product is usable end to end.

### Not included unless explicitly added later

- Automatically launching or stopping `llama-server`.
- Distributed runs across multiple machines.
- Web dashboard.
- Paid/cloud-only judge dependency as a required path.

## Design principles

- Build on Phase 1; do not rewrite working pieces.
- Keep the batch CLI scriptable.
- Keep local execution first.
- Assume the model server may be restarted between runs.
- Save raw outputs always.
- Make interrupted runs recoverable.
- Prefer deterministic scoring where possible.
- Keep official benchmark support modular and optional.
- Keep dependencies reasonable.

## Sequential task list

Complete these in order:

1. `tasks/01-freeze-phase-1-contract.md`
2. `tasks/02-design-phase-2-data-layout.md`
3. `tasks/03-create-benchmark-suite-registry.md`
4. `tasks/04-create-model-registry.md`
5. `tasks/05-add-server-health-checks.md`
6. `tasks/06-extract-reusable-runner.md`
7. `[HARD] tasks/07-HARD-structured-run-storage.md`
8. `tasks/08-save-coding-artifacts.md`
9. `[HARD] tasks/09-HARD-interrupt-safe-runs.md`
10. `[HARD] tasks/10-HARD-resume-incomplete-runs.md`
11. `tasks/11-create-core-benchmark-suites.md`
12. `tasks/12-add-coding-benchmark-suites.md`
13. `tasks/13-add-tool-calling-suite.md`
14. `tasks/14-add-long-context-suite.md`
15. `[HARD] tasks/15-HARD-official-benchmark-importers.md`
16. `tasks/16-improve-summary-and-leaderboard.md`
17. `[HARD] tasks/17-HARD-build-keyboard-terminal-ui.md`
18. `tasks/18-add-results-browser.md`
19. `tasks/19-update-readme-and-user-docs.md`
20. `[HARD] tasks/20-HARD-end-to-end-validation.md`

## Completion criteria

Phase 2 is complete when:

- `python bench_tui.py` launches a keyboard-driven terminal UI.
- The user can select an already-running model config.
- The app confirms server reachability before running.
- The user can select benchmark suites without editing code.
- Runs save under `results/runs/<model_id>/<run_id>/`.
- Each run has a manifest, raw result stream, summary, and saved artifacts.
- Coding outputs are saved as separate files.
- Ctrl+C or UI cancellation preserves completed results.
- Incomplete runs can be resumed.
- Summary and leaderboard files update after runs.
- At least one suite exists for math, real-world reasoning, instruction following, frontend coding, backend coding, misc coding, tool calling, and long-context.
- Official/open-source benchmark importing has at least one working path or a documented skip if the dataset is unavailable.
- The README explains setup, model config creation, running the TUI, running the batch CLI, and reading results.
- Tests pass.

## Verification command

At minimum, before marking Phase 2 complete:

```powershell
python -m pytest tests/ -q
python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --task-file benchmarks/reasoning/math.jsonl --dry-run
python bench_tui.py --smoke-test
```


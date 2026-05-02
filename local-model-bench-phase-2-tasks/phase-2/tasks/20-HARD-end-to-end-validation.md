# [HARD] Task 20 - End-to-End Validation

## Goal

Verify Phase 2 is ready for real local fine-tuned model benchmarking.

## Required checks

Run:

```powershell
python -m pytest tests/ -q
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --dry-run
python bench_tui.py --smoke-test
```

With a local `llama-server` running, manually verify:

```powershell
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --suite reasoning.math --repeats 1
python bench_tui.py
```

## Manual validation checklist

- Select model config in TUI.
- Health check shows reachable server.
- Select a benchmark suite.
- Run completes.
- Results folder is created under `results/runs/<model_id>/<run_id>/`.
- Manifest is complete.
- Raw JSONL contains one line per attempt.
- Summary is written.
- Leaderboard updates.
- Coding artifacts are saved for coding suites.
- Cancelling a run preserves completed attempts.
- Resuming a cancelled run skips completed attempts.

## Done criteria

- Automated tests pass.
- Smoke test passes.
- At least one real local model run succeeds.
- README instructions match the real workflow.
- Any known limitations are documented.


# Task 01 - Freeze Phase 1 Contract

## Goal

Document and protect the Phase 1 behavior that Phase 2 must build on.

Phase 2 should extend the harness without breaking the existing batch CLI.

## Required work

Create or update a concise contract document:

```text
docs/phase-1-contract.md
```

It should define:

- Valid model config fields.
- Valid JSONL task fields.
- Category-to-scorer behavior.
- Batch CLI arguments.
- Raw result object shape.
- Summary CSV columns.
- Leaderboard behavior.
- Backward-compatibility expectations.

## Required tests

Add or update tests proving:

- `run_benchmark.py --dry-run` still works with a sample task file.
- Existing scorers still accept the documented Phase 1 task format.
- Summary CSV still includes the Phase 1 columns.

## Done criteria

- Contract doc exists.
- Existing Phase 1 CLI behavior still works.
- Tests pass.


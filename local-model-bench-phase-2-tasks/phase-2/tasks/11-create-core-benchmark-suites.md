# Task 11 - Create Core Benchmark Suites

## Goal

Add useful non-coding benchmark suites for local model comparison.

## Required suites

Create:

```text
benchmarks/reasoning/math.jsonl
benchmarks/reasoning/real_world.jsonl
benchmarks/reasoning/instruction_following.jsonl
```

## Suite expectations

Each suite should contain enough tasks to be useful but not painfully slow for early runs.

Recommended starting counts:

- Math: 20 tasks.
- Real-world reasoning: 20 tasks.
- Instruction following: 20 tasks.

## Scoring

Use deterministic scorers where possible:

- `numeric_close` for numeric math.
- `exact_match` for constrained answers.
- `keyword_match` for short explanatory prompts.

## Done criteria

- Suites are valid JSONL.
- Suites are registered in `benchmarks/suites.yaml`.
- Dry-run works for every suite.
- Tests validate all benchmark files load.


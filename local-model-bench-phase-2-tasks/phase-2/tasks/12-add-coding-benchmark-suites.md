# Task 12 - Add Coding Benchmark Suites

## Goal

Add frontend, backend, and misc coding benchmark suites that produce inspectable artifacts.

## Required suites

Create:

```text
benchmarks/coding/frontend.jsonl
benchmarks/coding/backend.jsonl
benchmarks/coding/misc.jsonl
```

## Prompt style

Prompts should be practical and production-oriented.

Frontend examples:

- Build an accessible React component.
- Improve a CSS layout.
- Create a form with validation.

Backend examples:

- Implement a small API handler.
- Refactor data validation.
- Write a database query helper.

Misc examples:

- Write a script.
- Explain a bug and patch.
- Generate tests for a function.

## Scoring

For Phase 2, coding scoring can start with:

- Keyword/structure checks.
- Artifact preservation.
- Manual inspection support.

Do not require LLM-as-judge for completion.

## Done criteria

- All coding suites load.
- Outputs save as artifacts.
- Raw results link to artifact paths.
- README explains that coding scores are lightweight until a stronger judge is added.


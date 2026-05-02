# Task 14 - Add Long-Context Suite

## Goal

Add a suite for testing context handling, recall, and instruction retention.

## Required suite

Create:

```text
benchmarks/context/long_context.jsonl
```

## Task types

Include:

- Recall a fact from an earlier block.
- Follow an instruction buried in a long prompt.
- Summarize a long passage with required keywords.
- Compare details across two sections.

## Constraints

- Keep the initial suite small enough to run locally.
- Use deterministic scoring where possible.
- Include metadata with estimated context size.

## Done criteria

- Suite loads in dry-run mode.
- Tasks are long enough to exercise context, but not huge.
- Results record task category and prompt size metadata.


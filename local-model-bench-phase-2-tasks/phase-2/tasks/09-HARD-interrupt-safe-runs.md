# [HARD] Task 09 - Interrupt-Safe Runs

## Goal

Make benchmark runs safe to cancel without losing completed task results.

## Required behavior

- Write each attempt result to `raw.jsonl` immediately after it finishes.
- Flush writes so completed attempts survive Ctrl+C.
- Mark the manifest as `cancelled` when cancellation is detected.
- Preserve partial summaries for completed attempts.
- Do not corrupt JSONL files on interruption.

## Cancellation paths

Handle:

- Ctrl+C from batch CLI.
- Cancel action from the terminal UI.
- Exceptions during model calls.

## Done criteria

- Cancelling a run leaves a readable run folder.
- Completed attempts remain in `raw.jsonl`.
- Manifest status is `cancelled`.
- Tests simulate cancellation after one or more attempts.


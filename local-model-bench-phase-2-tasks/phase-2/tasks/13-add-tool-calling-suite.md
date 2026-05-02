# Task 13 - Add Tool Calling Suite

## Goal

Add a tool-calling benchmark suite using strict JSON output.

## Required suite

Create:

```text
benchmarks/tools/json_tool_calling.jsonl
```

## Required task patterns

Include prompts for:

- Weather lookup.
- Calculator.
- File search.
- Calendar event creation.
- Email drafting.
- Data extraction.
- Multi-argument tools.

## Required scoring

Use `json_valid` with:

```json
{
  "metadata": {
    "category": "json",
    "expected_tool": "tool_name",
    "required_argument_keys": ["key"]
  }
}
```

## Done criteria

- Suite covers at least 20 tool-call tasks.
- Invalid JSON gets clear failure reasons.
- Partial tool-call correctness receives partial credit.
- Dry-run and normal scoring paths work.


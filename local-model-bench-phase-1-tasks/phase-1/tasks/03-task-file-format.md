# Task 03 — Define Task File Format

## Goal

Create JSONL benchmark task files.

Each line in a task file represents one benchmark task.

## Required task schema

Each task should support these fields:

```json
{
  "id": "math_001",
  "category": "math",
  "prompt": "What is 17% of 850? Give only the number.",
  "expected": "144.5",
  "scorer": "exact_match"
}
```

Some scorers may need different expected fields, for example:

```json
{
  "id": "general_001",
  "category": "general",
  "prompt": "Explain the difference between model weights memory and KV cache memory in simple terms.",
  "expected_keywords": ["weights", "KV cache", "context", "tokens"],
  "scorer": "keyword_match"
}
```

## Required files

Create these files:

```text
tasks/math/basic_math.jsonl
tasks/general/local_ai.jsonl
tasks/coding/basic_coding.jsonl
tasks/tool_use/basic_tool_format.jsonl
```

## Required task counts for Phase 1

Keep Phase 1 small:

- `tasks/math/basic_math.jsonl`: 10 tasks
- `tasks/general/local_ai.jsonl`: 10 tasks
- `tasks/coding/basic_coding.jsonl`: 5 tasks
- `tasks/tool_use/basic_tool_format.jsonl`: 5 tasks

Total: 30 tasks.

## Suggested math tasks

Include prompts such as:

```json
{"id":"math_001","category":"math","prompt":"What is 17% of 850? Give only the number.","expected":"144.5","scorer":"numeric_close"}
{"id":"math_002","category":"math","prompt":"A model runs at 54.1 tok/s and another runs at 33.1 tok/s. What is the percent speed drop from the first to the second? Round to one decimal place. Give only the number.","expected":"38.8","scorer":"numeric_close"}
{"id":"math_003","category":"math","prompt":"If a model uses 9.85 GB of VRAM and another setting uses 12.25 GB, how much more VRAM is used? Give only the number in GB.","expected":"2.4","scorer":"numeric_close"}
```

## Suggested general/local AI tasks

Include prompts about:

- model weights vs KV cache
- quantization basics
- context window behavior
- why bigger models may be slower
- prompt eval vs generation speed
- flash attention
- GPU layers
- VRAM vs RAM
- local model limitations
- repeatable benchmarking

Use `keyword_match` scoring.

## Suggested coding tasks

For Phase 1, coding tasks can be simple prompt-only tasks scored with keyword matching or exact expected snippets.

Example:

```json
{"id":"coding_001","category":"coding","prompt":"Write a Python function named add that returns the sum of two arguments. Return only the code.","expected_keywords":["def add","return"],"scorer":"keyword_match"}
```

Later phases can use real file-editing and unit tests.

## Suggested tool-use tasks

For Phase 1, test whether the model can produce valid JSON tool calls.

Example:

```json
{"id":"tool_001","category":"tool_use","prompt":"You have a tool named calculator. Return a JSON object calling calculator to compute 17% of 850. Use this format: {\"tool\":\"calculator\",\"arguments\":{\"expression\":\"...\"}}. Return only JSON.","scorer":"json_valid"}
```

## Required implementation

Create:

```text
runners/task_loader.py
```

It should expose:

```python
def load_tasks(path: str) -> list[dict]:
    ...
```

Requirements:

- Read JSONL.
- Ignore blank lines.
- Validate each task has:
  - `id`
  - `category`
  - `prompt`
  - `scorer`
- Return a list of task dictionaries.
- Raise clear errors for invalid JSON or missing fields.

## Done criteria

This task is done when:

- All four JSONL task files exist.
- Total Phase 1 task count is 30.
- `runners/task_loader.py` exists.
- Task loader can load all task files.
- Invalid task lines produce clear errors.

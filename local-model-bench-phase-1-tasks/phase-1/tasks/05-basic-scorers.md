# Task 05 — Build Basic Scorers

## Goal

Create simple scoring functions for Phase 1 tasks.

Scorers should be deterministic, lightweight, and easy to extend later.

## Required files

Create:

```text
scorers/exact_match.py
scorers/numeric_close.py
scorers/keyword_match.py
scorers/json_valid.py
scorers/registry.py
```

## Common scorer return format

Every scorer must return:

```python
{
    "score": 1.0,
    "passed": True,
    "reason": "Matched expected answer"
}
```

or:

```python
{
    "score": 0.0,
    "passed": False,
    "reason": "Expected 144.5 but got 145"
}
```

## Scorer 1: exact_match

File:

```text
scorers/exact_match.py
```

Behavior:

- Compare normalized expected and actual strings.
- Strip whitespace.
- Case-insensitive by default.

Function:

```python
def score(task: dict, response: str) -> dict:
    ...
```

## Scorer 2: numeric_close

File:

```text
scorers/numeric_close.py
```

Behavior:

- Extract the first number from the response.
- Compare it to `task["expected"]` as a float.
- Default tolerance: `0.01`.
- Allow optional task-level tolerance:

```json
{"tolerance": 0.1}
```

Function:

```python
def score(task: dict, response: str) -> dict:
    ...
```

## Scorer 3: keyword_match

File:

```text
scorers/keyword_match.py
```

Behavior:

- Read `task["expected_keywords"]`.
- Count how many keywords appear in the response.
- Case-insensitive.
- Score = matched keywords / total keywords.
- Passed if score >= 0.7 by default.
- Allow optional threshold:

```json
{"threshold": 0.8}
```

Function:

```python
def score(task: dict, response: str) -> dict:
    ...
```

## Scorer 4: json_valid

File:

```text
scorers/json_valid.py
```

Behavior:

- Response must parse as valid JSON.
- If task includes `expected_tool`, check that `parsed["tool"]` matches.
- If task includes `required_argument_keys`, check that those keys exist inside `parsed["arguments"]`.

Example task:

```json
{
  "id": "tool_001",
  "category": "tool_use",
  "prompt": "Return JSON calling calculator...",
  "scorer": "json_valid",
  "expected_tool": "calculator",
  "required_argument_keys": ["expression"]
}
```

Function:

```python
def score(task: dict, response: str) -> dict:
    ...
```

## Scorer registry

Create:

```text
scorers/registry.py
```

Expose:

```python
def get_scorer(name: str):
    ...
```

Supported names:

```text
exact_match
numeric_close
keyword_match
json_valid
```

If an unknown scorer is requested, raise a clear `ValueError`.

## Done criteria

This task is done when:

- All four scorer files exist.
- `scorers/registry.py` exists.
- Each scorer returns the common scoring format.
- Each scorer handles bad input gracefully.
- Unknown scorer names raise clear errors.

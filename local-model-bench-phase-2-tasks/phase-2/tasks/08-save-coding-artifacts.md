# Task 08 - Save Coding Artifacts

## Goal

Save model-generated coding outputs as standalone files so frontend/backend/misc coding benchmark responses are easy to inspect.

## Required behavior

For tasks with coding categories, write files under:

```text
results/runs/<model_id>/<run_id>/artifacts/<suite_id>/
```

Example:

```text
artifacts/coding.frontend/frontend_component_001_response.md
artifacts/coding.backend/api_handler_001_response.py
```

## Task metadata

Support optional task metadata:

```json
{
  "metadata": {
    "category": "code",
    "artifact_extension": ".tsx",
    "artifact_kind": "frontend"
  }
}
```

If no extension is supplied, default to `.md`.

## Done criteria

- Coding responses are saved as separate files.
- Raw JSONL still includes the full response.
- Artifact paths are recorded in each raw result.
- Tests cover extension selection and path sanitization.


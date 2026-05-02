# Results Layout

> Defines the on-disk layout for Phase 2 benchmark run results.
> Builds on the Phase 1 contract without breaking existing paths.

## Target Directory Tree

```
results/
  summary.csv                           -- Phase 1 (still updated)
  reports/
    leaderboard.md                      -- Phase 1 (still updated)
  runs/
    <model_id>/
      <run_id>/
        manifest.json
        raw.jsonl
        summary.json
        artifacts/
          <suite_id>/
            <task_id>_response.<ext>
            ...
```

## Naming Rules

### model_id

- Kebab-case, alphanumeric with hyphens only.
- Matches the id field in the model YAML config.
- Examples: qwen-9b-q8-4k, llama-3-8b, phi-4.

### run_id

- Timestamp-based: YYYY-MM-DD_HH-MM-SS (24-hour, no colons - Windows-safe).
- A short random suffix may be appended for uniqueness when runs start in the same second.
- Full pattern: YYYY-MM-DD_HH-MM-SS or YYYY-MM-DD_HH-MM-SS_<8hex>.
- Examples: 2026-05-02_14-30-00, 2026-05-02_14-30-00_a1b2c3d4.

### suite_id

- Dot-separated <category>.<name>.
- Category and name are lowercase alphanumeric with hyphens.
- Examples: reasoning.math, coding.frontend, tools.json_tool_calling.

## Run Folder Structure

```
results/runs/<model_id>/<run_id>/
```

Created before the first model API call (interrupt-safe creation).

### manifest.json

Written at run start, updated on completion/cancellation/failure.

**Allowed statuses:**

| Status    | Meaning                                                |
|-----------|--------------------------------------------------------|
| running   | Run is in progress                                     |
| completed | All attempts completed successfully                    |
| cancelled | User interrupted or cancelled the run                  |
| failed    | Run terminated due to unrecoverable error              |

**Manifest JSON fields:**

| Field             | Type   | Description                                      |
|-------------------|--------|--------------------------------------------------|
| run_id            | str    | Timestamp-based unique ID                        |
| model_config_id   | str    | From config id field                             |
| model_name        | str    | Human-readable model name                        |
| suite_id          | str    | Suite identifier                                 |
| suite_name        | str    | Human-readable suite name                        |
| task_file         | str    | Path to the source JSONL task file               |
| server_url        | str    | OpenAI-compatible endpoint URL                   |
| settings          | dict   | Generation settings snapshot                     |
| status            | str    | One of: running, completed, cancelled, failed    |
| started_at        | str    | ISO 8601 timestamp                               |
| completed_at      | str    | ISO 8601 timestamp or null                       |
| repeats           | int    | Number of repeats configured                     |
| total_tasks       | int    | Number of unique tasks                           |
| total_attempts    | int    | Total attempts (tasks x repeats)                 |

### raw.jsonl

One JSON object per completed attempt. Appended immediately after each attempt finishes and flushed to disk.

**Object shape (Phase 1 contract fields + Phase 2 additions):**

| Key             | Type  | Description                                          |
|-----------------|-------|------------------------------------------------------|
| run_id          | str   | Timestamp-based unique ID                            |
| model_config_id | str   | From config id field                                 |
| task_id         | str   | From task id field                                   |
| category        | str   | From metadata.category, or general if missing        |
| task_file       | str   | Path to the source JSONL file                        |
| prompt          | str   | The description field sent as the user prompt        |
| expected        | str   | The expected_output field                            |
| response        | str   | Model response text, or error message                |
| latency_sec     | float | Wall-clock time for the API call                     |
| score           | float | Scorer output (0.0-1.0)                              |
| passed          | bool  | Whether the attempt passed                           |
| reason          | str   | Scorer human-readable explanation                    |
| settings        | dict  | The generation settings used                         |
| repeat_index    | int   | Zero-based repeat number                             |
| repeat_count    | int   | Total repeats configured                             |
| artifact_paths  | list  | Paths to saved artifact files (empty if not applicable) |

### summary.json

Aggregate data for the run. Written/updated after the run completes or is cancelled.

**Summary JSON fields:**

| Field               | Type   | Description                                      |
|---------------------|--------|--------------------------------------------------|
| run_id              | str    | Timestamp-based unique ID                        |
| model_config_id     | str    | From config id field                             |
| model_name          | str    | Human-readable model name                        |
| suite_id            | str    | Suite identifier                                 |
| suite_name          | str    | Human-readable suite name                        |
| task_file           | str    | Path to the source JSONL file                    |
| run_folder          | str    | Full run folder path                             |
| status              | str    | One of: completed, cancelled, failed             |
| total_tasks         | int    | Number of unique tasks                           |
| total_attempts      | int    | Total attempts (tasks x repeats)                 |
| passed              | int    | Number of passed attempts                        |
| failed              | int    | Number of failed attempts                        |
| pass_rate           | float  | passed / total_attempts                          |
| average_score       | float  | Mean score across all attempts                   |
| average_latency_sec | float  | Mean latency in seconds                          |
| repeats             | int    | Repeat count                                     |
| artifact_count      | int    | Number of saved artifact files                   |
| started_at          | str    | ISO 8601 timestamp                               |
| completed_at        | str    | ISO 8601 timestamp                               |

### artifacts/<suite_id>/

For coding and artifact-generating tasks, model responses are saved as standalone files.

**Rules:**

- Artifact file extension comes from metadata.artifact_extension in the task. Defaults to .md if not provided.
- Task IDs are sanitized before use in filenames: replace non-alphanumeric characters (except -, _) with _.
- Artifact paths are recorded in the artifact_paths field of the corresponding raw.jsonl entry.
- The full response text is still preserved in raw.jsonl. Artifacts are an additional copy for convenience.

## Backward Compatibility

The following Phase 1 paths continue to work:

- results/summary.csv - still updated with each run
- results/reports/leaderboard.md - still regenerated after each run
- results/raw/<config_id>/ - Phase 1 raw output files are left in place (not actively written by the new runner, but not deleted)

## Windows Compatibility

- run_id timestamps use hyphens instead of colons (14-30-00 not 14:30:00) to avoid Windows filename restrictions.
- All paths use forward slashes in documentation; Windows backslashes work identically.
- Long paths are supported via the \\?\ prefix if needed, but not required for typical usage.

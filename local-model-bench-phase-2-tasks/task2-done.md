# Task 02 — Design Phase 2 Data Layout ✅

## Deliverables

### `docs/results_layout.md`

Documents the complete Phase 2 results folder structure:

- **Target directory tree** under `results/runs/<model_id>/<run_id>/`
- **Naming rules** for `model_id` (kebab-case), `run_id` (timestamp-based, no colons), `suite_id` (dot-separated)
- **Run folder layout** with `manifest.json`, `raw.jsonl`, `summary.json`, `artifacts/<suite_id>/`
- **Manifest schema** and all allowed statuses: `running`, `completed`, `cancelled`, `failed`
- **raw.jsonl** result object shape (Phase 1 fields + new `artifact_paths`)
- **summary.json** aggregate schema
- **Artifact rules**: file extensions, sanitization, path recording
- **Backward compatibility**: existing `summary.csv`, `leaderboard.md`, and `results/raw/` remain
- **Windows compatibility**: colon-safe timestamps, forward/backward slash support

### `docs/benchmark_suite_format.md`

Documents the complete benchmark suite structure and JSONL task format:

- **Target directory tree** under `benchmarks/` (coding, reasoning, tools, context, official)
- **Suite registry** format at `benchmarks/suites.yaml` with 8 initial suites
- **Suite ID naming** convention `<category>.<name>`
- **Required JSONL fields** (Phase 1 contract)
- **Phase 2 metadata fields** table: `category`, `keywords`, `tolerance`, `threshold`, `expected_tool`, `required_argument_keys`, `artifact_kind`, `artifact_extension`, `estimated_context_tokens`
- **Example tasks**: math, coding, tool calling, long-context
- **Scoring strategy**: deterministic scorers table + coding benchmark notes
- **Official benchmark import conventions**
- **Windows compatibility** notes

## Done Criteria Met

| Criteria | Status |
|----------|--------|
| Target layout documented | ✅ 162 lines in `docs/results_layout.md` |
| Naming rules for `model_id`, `suite_id`, `run_id` explicit | ✅ All three documented |
| Layout supports multiple models and multiple runs per model | ✅ `results/runs/<model_id>/<run_id>/` structure |
| Layout is Windows-friendly | ✅ Colon-safe timestamps, forward/backward slash support documented |

## Verification

```
docs/results_layout.md: 162 lines
  - All required sections present
docs/benchmark_suite_format.md: 238 lines
  - All required sections present
```

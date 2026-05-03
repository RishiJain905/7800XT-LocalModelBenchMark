# Task 12 - Add Coding Benchmark Suites Done

Completed: 2026-05-03

## Summary

- Populated `benchmarks/coding/frontend.jsonl` with 10 practical frontend coding tasks.
- Populated `benchmarks/coding/backend.jsonl` with 10 practical backend coding tasks.
- Populated `benchmarks/coding/misc.jsonl` with 10 practical miscellaneous coding tasks.
- Added README guidance explaining that Phase 2 coding scores are lightweight keyword/structure checks and that full coding outputs are preserved as artifacts.

## Confirmations

- The registered coding suites load through `benchmarks/suites.yaml`.
- Each coding suite contains 10 tasks.
- Each coding task uses `metadata.category: "code"` and includes artifact metadata plus keyword scoring metadata.
- Artifact-path behavior is covered by a runner test that verifies coding responses are saved to `artifacts/<suite_id>/` and linked from `artifact_paths`.

## Verification

```powershell
python -m pytest tests/ -q
# 380 passed in 1.29s

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite coding.frontend --dry-run
# Loaded 10 tasks for coding.frontend using keyword_match.

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite coding.backend --dry-run
# Loaded 10 tasks for coding.backend using keyword_match.

python run_benchmark.py --config configs/qwen-9b-q8-4k.yaml --suite coding.misc --dry-run
# Loaded 10 tasks for coding.misc using keyword_match.
```

# Task 15 Done - Official Benchmark Importers

Implemented stdlib-only official benchmark importers at `scripts/import_benchmark.py`.

What changed:

- Added `--source gsm8k|mmlu|mbpp|humaneval`, `--input`, `--limit`, `--output`, and `--force`.
- Converts local GSM8K-style JSONL records into harness math tasks.
- Converts local MMLU-style CSV or JSONL records into multiple-choice tasks.
- Converts local MBPP-style JSONL records into Python code artifact tasks.
- Converts local HumanEval-style JSONL records into Python code artifact tasks.
- Extracts final answers after GSM8K's `####` marker when present.
- Preserves source attribution and importer metadata.
- Validates generated files through the existing task format in tests.
- Handles local UTF-8 and UTF-8 BOM JSONL inputs.
- Avoids downloads and new dependencies.
- Documents dataset access/licensing caveats in `benchmarks/official/README.md`.
- Keeps generated official JSON/JSONL imports ignored by default.

Verification run:

```powershell
python -m pytest tests/test_import_benchmark.py -q
python -m pytest tests/ -q
python scripts/import_benchmark.py --source gsm8k --input <tiny_fixture> --limit 1 --output <tmp_output> --force
```

Results:

- `12 passed` for importer tests.
- `396 passed` for the full test suite.
- Tiny local CLI imports wrote valid GSM8K, MMLU, MBPP, and HumanEval tasks.

Notes:

- Official datasets are user-supplied local files.
- The importer does not use Hugging Face, `datasets`, or network access.
- Generated imports under `benchmarks/official/` are ignored by default and should be run directly with `--task-file`.
- MBPP and HumanEval are artifact-oriented in Phase 2 because this harness does not yet execute code tests.

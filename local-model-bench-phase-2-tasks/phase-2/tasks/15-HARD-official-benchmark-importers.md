# [HARD] Task 15 - Official Benchmark Importers

## Goal

Add optional support for importing official/open-source benchmark datasets into this harness's JSONL format.

## Recommended first targets

Start with datasets that are practical for local runs:

- GSM8K-style math subset.
- HumanEval or MBPP-style coding subset, if licensing and format are acceptable.
- MMLU-style multiple-choice subset, if dataset access is straightforward.

## Required structure

Create:

```text
scripts/import_benchmark.py
benchmarks/official/README.md
benchmarks/official/.gitkeep
```

## Required behavior

The importer should:

- Convert supported source data into benchmark JSONL.
- Preserve source attribution metadata.
- Allow limiting task count.
- Avoid committing large downloaded datasets by default.
- Fail with clear instructions when a source dataset is unavailable.

## Example command

```powershell
python scripts/import_benchmark.py --source gsm8k --limit 50 --output benchmarks/official/gsm8k_sample.jsonl
```

## Done criteria

- At least one official/open-source importer works or has a documented skip path.
- Imported files pass task validation.
- README explains dataset licensing/access caveats.
- Tests cover importer conversion with a tiny local fixture.


# Official / Open-Source Benchmarks

This directory is for user-generated imports of official/open-source benchmark
datasets into this harness's JSONL task format.

Generated dataset files are intentionally ignored by git. Keep source datasets
outside the repository or place only small local samples here when needed for
manual testing.

## GSM8K

The importer supports GSM8K-style local JSONL files with one object per line:

```json
{"question": "What is 2 + 2?", "answer": "2 + 2 = 4\n#### 4"}
```

Import a limited local sample:

```powershell
python scripts/import_benchmark.py --source gsm8k --input path\to\gsm8k.jsonl --limit 50 --output benchmarks/official/gsm8k_sample.jsonl
```

Overwrite an existing generated file:

```powershell
python scripts/import_benchmark.py --source gsm8k --input path\to\gsm8k.jsonl --limit 50 --output benchmarks/official/gsm8k_sample.jsonl --force
```

## MMLU

The importer supports local MMLU-style CSV files with `question`, `A`, `B`,
`C`, `D`, and `answer` columns, plus an optional `subject` column. It also
supports JSONL rows with `question`, `choices`, `answer`, and optional
`subject`.

```powershell
python scripts/import_benchmark.py --source mmlu --input path\to\mmlu.csv --limit 50 --output benchmarks/official/mmlu_sample.jsonl
```

MMLU imports are formatted as multiple-choice tasks and scored by exact option
letter matching.

## MBPP

The importer supports local MBPP-style JSONL rows with `task_id`, `text`, and
`test_list` fields.

```powershell
python scripts/import_benchmark.py --source mbpp --input path\to\mbpp.jsonl --limit 50 --output benchmarks/official/mbpp_sample.jsonl
```

MBPP imports preserve provided tests in the prompt and metadata. Phase 2 does
not execute generated code, so these are code artifact tasks for lightweight
keyword/manual review until sandboxed code judging is added.

## HumanEval

The importer supports local HumanEval-style JSONL rows with `task_id`,
`prompt`, `entry_point`, and `test` fields.

```powershell
python scripts/import_benchmark.py --source humaneval --input path\to\humaneval.jsonl --limit 50 --output benchmarks/official/humaneval_sample.jsonl
```

HumanEval imports preserve prompt, entry point, and tests in task metadata.
Like MBPP, these are artifact-oriented code tasks in Phase 2, not full
deterministic code execution benchmarks.

## Running Imported Files

Run the imported tasks directly:

```powershell
python run_benchmark.py --config configs/models/qwen-9b-q8-4k.yaml --task-file benchmarks/official/gsm8k_sample.jsonl --dry-run
```

## Dataset Access And Licensing

The importer does not download datasets and does not require Hugging Face,
`datasets`, or network access. Download or export source data yourself, review
the dataset's license and access terms, then point `--input` at the local file.

Large source datasets and generated imports should not be committed to this
repository. If a dataset is unavailable, the importer exits with instructions
for providing a local file.

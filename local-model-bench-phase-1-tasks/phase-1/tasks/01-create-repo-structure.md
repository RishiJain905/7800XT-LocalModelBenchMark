# Task 01 — Create Repo Structure

## Goal

Create the base project folder structure for the local model benchmark harness.

This task does not implement benchmark logic yet. It only creates the repo layout and placeholder files so future tasks have clear locations.

## Required structure

Create this structure at the repository root:

```text
.
├─ configs/
│
├─ tasks/
│  ├─ math/
│  ├─ coding/
│  ├─ tool_use/
│  └─ general/
│
├─ runners/
│  └─ __init__.py
│
├─ scorers/
│  └─ __init__.py
│
├─ results/
│  ├─ raw/
│  └─ reports/
│
├─ scripts/
│
├─ run_benchmark.py
├─ requirements.txt
└─ README.md
```

## Files to create

### `requirements.txt`

Start with:

```txt
requests>=2.31.0
PyYAML>=6.0.0
```

### `run_benchmark.py`

Create a placeholder file with a simple CLI stub:

```python
from __future__ import annotations


def main() -> None:
    print("Local Model Benchmark Harness - Phase 1")


if __name__ == "__main__":
    main()
```

### `README.md`

Update the placeholder README with the following:

```markdown
# Local Model Benchmark Harness

A lightweight benchmark harness for comparing local LLMs and runtime settings through `llama-server`.
```

## Done criteria

This task is done when:

- All folders exist.
- `run_benchmark.py` exists and can be executed.
- `requirements.txt` exists.
- `README.md` exists.
- `runners/__init__.py` and `scorers/__init__.py` exist.

Test with:

```powershell
python run_benchmark.py
```

Expected output:

```text
Local Model Benchmark Harness - Phase 1
```

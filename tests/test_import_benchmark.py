"""Tests for scripts/import_benchmark.py official benchmark importer."""

from __future__ import annotations

import importlib.util
import csv
import json
from pathlib import Path

import pytest

from runners.task_loader import load_tasks


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "import_benchmark.py"


def _load_importer_module():
    spec = importlib.util.spec_from_file_location("import_benchmark", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_gsm8k_fixture(path: Path) -> None:
    records = [
        {
            "question": "Jan has 3 apples and buys 4 more. How many apples?",
            "answer": "Jan has 3 + 4 = 7 apples.\n#### 7",
        },
        {
            "question": "A box has 12 pens split across 3 bags. Pens per bag?",
            "answer": "12 / 3 = 4\n#### 4",
        },
    ]
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def test_gsm8k_fixture_converts_to_valid_harness_tasks(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "gsm8k.jsonl"
    output_path = tmp_path / "out.jsonl"
    _write_gsm8k_fixture(source_path)

    written = importer.import_gsm8k(source_path, output_path, limit=None, force=False)

    assert written == 2
    tasks = load_tasks(str(output_path))
    assert len(tasks) == 2
    assert tasks[0]["id"] == "gsm8k_000001"
    assert tasks[0]["command"] == "noop"
    assert tasks[0]["expected_output"] == "7"
    assert tasks[0]["description"].endswith("Reply with only the final answer.")
    assert tasks[0]["metadata"]["category"] == "math"
    assert tasks[0]["metadata"]["source"] == "gsm8k"
    assert tasks[0]["metadata"]["source_file"] == "gsm8k.jsonl"
    assert tasks[0]["metadata"]["source_record_index"] == 0
    assert tasks[0]["metadata"]["importer"] == "gsm8k_local_jsonl"


def test_gsm8k_import_respects_limit(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "gsm8k.jsonl"
    output_path = tmp_path / "limited.jsonl"
    _write_gsm8k_fixture(source_path)

    written = importer.import_gsm8k(source_path, output_path, limit=1, force=False)

    assert written == 1
    assert len(load_tasks(str(output_path))) == 1


def test_gsm8k_answer_without_marker_uses_full_answer(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "gsm8k.jsonl"
    output_path = tmp_path / "out.jsonl"
    source_path.write_text(
        json.dumps({"question": "What is 5 + 6?", "answer": "11"}) + "\n",
        encoding="utf-8",
    )

    importer.import_gsm8k(source_path, output_path, limit=None, force=False)

    tasks = load_tasks(str(output_path))
    assert tasks[0]["expected_output"] == "11"


def test_gsm8k_import_accepts_utf8_bom_input(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "gsm8k_bom.jsonl"
    output_path = tmp_path / "out.jsonl"
    source_path.write_text(
        json.dumps({"question": "What is 1 + 2?", "answer": "#### 3"}) + "\n",
        encoding="utf-8-sig",
    )

    importer.import_gsm8k(source_path, output_path, limit=None, force=False)

    tasks = load_tasks(str(output_path))
    assert tasks[0]["expected_output"] == "3"


def test_missing_input_exits_with_clear_dataset_instructions(capsys):
    importer = _load_importer_module()

    with pytest.raises(SystemExit) as exc_info:
        importer.main(
            [
                "--source",
                "gsm8k",
                "--output",
                "benchmarks/official/gsm8k_sample.jsonl",
            ]
        )

    assert exc_info.value.code == 2
    assert "provide a local GSM8K JSONL file" in capsys.readouterr().err


def test_existing_output_requires_force(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "gsm8k.jsonl"
    output_path = tmp_path / "out.jsonl"
    _write_gsm8k_fixture(source_path)
    output_path.write_text("already here\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        importer.import_gsm8k(source_path, output_path, limit=None, force=False)


def test_force_allows_overwriting_existing_output(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "gsm8k.jsonl"
    output_path = tmp_path / "out.jsonl"
    _write_gsm8k_fixture(source_path)
    output_path.write_text("already here\n", encoding="utf-8")

    importer.import_gsm8k(source_path, output_path, limit=1, force=True)

    assert len(load_tasks(str(output_path))) == 1


def test_mmlu_csv_fixture_converts_to_valid_harness_tasks(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "mmlu.csv"
    output_path = tmp_path / "mmlu.jsonl"
    with source_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["question", "A", "B", "C", "D", "answer", "subject"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "question": "Which planet is closest to the Sun?",
                "A": "Venus",
                "B": "Mercury",
                "C": "Earth",
                "D": "Mars",
                "answer": "B",
                "subject": "astronomy",
            }
        )

    written = importer.import_mmlu(source_path, output_path, limit=None, force=False)

    assert written == 1
    tasks = load_tasks(str(output_path))
    assert tasks[0]["id"] == "mmlu_000001"
    assert tasks[0]["command"] == "noop"
    assert tasks[0]["expected_output"] == "B"
    assert "A. Venus" in tasks[0]["description"]
    assert "Reply with only the correct option letter." in tasks[0]["description"]
    assert tasks[0]["metadata"]["category"] == "text"
    assert tasks[0]["metadata"]["source"] == "mmlu"
    assert tasks[0]["metadata"]["subject"] == "astronomy"


def test_mmlu_jsonl_fixture_with_choices_converts_to_valid_harness_tasks(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "mmlu.jsonl"
    output_path = tmp_path / "mmlu_out.jsonl"
    _write_jsonl(
        source_path,
        [
            {
                "question": "Water freezes at what temperature in Celsius?",
                "choices": ["0", "50", "100", "212"],
                "answer": 0,
                "subject": "science",
            }
        ],
    )

    importer.import_mmlu(source_path, output_path, limit=None, force=False)

    tasks = load_tasks(str(output_path))
    assert tasks[0]["expected_output"] == "A"
    assert "A. 0" in tasks[0]["description"]


def test_mbpp_fixture_converts_to_valid_code_tasks(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "mbpp.jsonl"
    output_path = tmp_path / "mbpp_out.jsonl"
    _write_jsonl(
        source_path,
        [
            {
                "task_id": 11,
                "text": "Write a function add_one that returns n + 1.",
                "test_list": ["assert add_one(1) == 2"],
            }
        ],
    )

    written = importer.import_mbpp(source_path, output_path, limit=None, force=False)

    assert written == 1
    tasks = load_tasks(str(output_path))
    assert tasks[0]["id"] == "mbpp_11"
    assert tasks[0]["expected_output"] == "Pass provided tests"
    assert "assert add_one(1) == 2" in tasks[0]["description"]
    assert tasks[0]["metadata"]["category"] == "code"
    assert tasks[0]["metadata"]["artifact_extension"] == ".py"
    assert tasks[0]["metadata"]["source"] == "mbpp"
    assert tasks[0]["metadata"]["source_task_id"] == 11
    assert tasks[0]["metadata"]["test_list"] == ["assert add_one(1) == 2"]


def test_humaneval_fixture_converts_to_valid_code_tasks(tmp_path):
    importer = _load_importer_module()
    source_path = tmp_path / "humaneval.jsonl"
    output_path = tmp_path / "humaneval_out.jsonl"
    _write_jsonl(
        source_path,
        [
            {
                "task_id": "HumanEval/0",
                "prompt": "def add(a, b):\n    \"\"\"Return a + b.\"\"\"\n",
                "entry_point": "add",
                "test": "assert add(2, 3) == 5",
            }
        ],
    )

    written = importer.import_humaneval(
        source_path, output_path, limit=None, force=False
    )

    assert written == 1
    tasks = load_tasks(str(output_path))
    assert tasks[0]["id"] == "humaneval_0"
    assert tasks[0]["expected_output"] == "Pass provided tests"
    assert "def add(a, b):" in tasks[0]["description"]
    assert "assert add(2, 3) == 5" in tasks[0]["description"]
    assert tasks[0]["metadata"]["category"] == "code"
    assert tasks[0]["metadata"]["source"] == "humaneval"
    assert tasks[0]["metadata"]["entry_point"] == "add"
    assert tasks[0]["metadata"]["source_task_id"] == "HumanEval/0"


def test_cli_accepts_new_supported_sources_for_missing_input(capsys):
    importer = _load_importer_module()

    for source in ["mmlu", "mbpp", "humaneval"]:
        with pytest.raises(SystemExit) as exc_info:
            importer.main(
                [
                    "--source",
                    source,
                    "--output",
                    f"benchmarks/official/{source}_sample.jsonl",
                ]
            )
        assert exc_info.value.code == 2
        assert f"provide a local {source.upper()}" in capsys.readouterr().err

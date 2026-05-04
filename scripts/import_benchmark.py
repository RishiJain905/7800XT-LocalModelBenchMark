"""Import official/open-source benchmark data into harness JSONL tasks."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


IMPORTER_VERSION = "1"
INPUT_HELP: dict[str, str] = {
    "gsm8k": (
        "GSM8K import requires --input pointing to a local GSM8K-style JSONL file. "
        "Download, export, or provide a local GSM8K JSONL file yourself, "
        "review its license/access terms, "
        "then rerun with --input path\\to\\gsm8k.jsonl."
    ),
    "mmlu": (
        "MMLU import requires --input pointing to a local MMLU CSV or JSONL file. "
        "Download, export, or provide a local MMLU file yourself, "
        "review its license/access terms, "
        "then rerun with --input path\\to\\mmlu.csv."
    ),
    "mbpp": (
        "MBPP import requires --input pointing to a local MBPP-style JSONL file. "
        "Download, export, or provide a local MBPP JSONL file yourself, "
        "review its license/access terms, "
        "then rerun with --input path\\to\\mbpp.jsonl."
    ),
    "humaneval": (
        "HumanEval import requires --input pointing to a local HumanEval-style JSONL file. "
        "Download, export, or provide a local HUMANEVAL JSONL file yourself, "
        "review its license/access terms, "
        "then rerun with --input path\\to\\humaneval.jsonl."
    ),
}
SUPPORTED_SOURCES = tuple(INPUT_HELP)
OPTION_LETTERS = ("A", "B", "C", "D")


def read_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    """Yield JSON objects from a JSONL file with zero-based record indexes."""
    with path.open("r", encoding="utf-8-sig") as f:
        for record_index, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}: invalid JSON on line {record_index + 1}: {exc.msg}"
                ) from exc
            if not isinstance(record, dict):
                raise ValueError(
                    f"{path}: line {record_index + 1} must be a JSON object"
                )
            yield record_index, record


def ensure_can_write(input_path: Path, output_path: Path, limit: int | None, force: bool) -> None:
    """Validate common import file arguments."""
    if not input_path.is_file():
        source = _guess_source_from_output(output_path)
        help_text = INPUT_HELP.get(source, "Provide a local source dataset file.")
        raise FileNotFoundError(f"{help_text} Missing file: {input_path}")
    if output_path.exists() and not force:
        raise FileExistsError(
            f"Output already exists: {output_path}. Pass --force to overwrite it."
        )
    if limit is not None and limit <= 0:
        raise ValueError("--limit must be a positive integer")


def _guess_source_from_output(output_path: Path) -> str:
    stem = output_path.stem.lower()
    for source in SUPPORTED_SOURCES:
        if source in stem:
            return source
    return ""


def clean_id_part(value: Any) -> str:
    """Return a stable ASCII-ish identifier suffix."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_").lower()
    return cleaned or "unknown"


def source_metadata(source: str, source_path: Path, record_index: int) -> dict[str, Any]:
    """Build common source attribution metadata."""
    importer = "gsm8k_local_jsonl" if source == "gsm8k" else f"{source}_local_file"
    return {
        "source": source,
        "source_attribution": f"{source.upper()} (user-provided local dataset file)",
        "source_file": source_path.name,
        "source_path": str(source_path),
        "source_record_index": record_index,
        "importer": importer,
        "importer_version": IMPORTER_VERSION,
    }


def extract_gsm8k_final_answer(answer: str) -> str:
    """Return the final answer after GSM8K's #### marker when present."""
    if "####" in answer:
        return answer.rsplit("####", 1)[1].strip()
    return answer.strip()


def convert_gsm8k_record(
    record: dict[str, Any],
    record_index: int,
    source_path: Path,
) -> dict[str, Any]:
    """Convert one GSM8K-style record to this harness's task format."""
    question = record.get("question")
    answer = record.get("answer")
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"{source_path}: record {record_index} has no question")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"{source_path}: record {record_index} has no answer")

    expected_output = extract_gsm8k_final_answer(answer)
    if not expected_output:
        raise ValueError(f"{source_path}: record {record_index} has an empty answer")

    task_number = record_index + 1
    return {
        "id": f"gsm8k_{task_number:06d}",
        "description": (
            f"{question.strip()}\n\nReply with only the final answer."
        ),
        "command": "noop",
        "expected_output": expected_output,
        "metadata": {
            "category": "math",
            **source_metadata("gsm8k", source_path, record_index),
        },
    }


def write_tasks_jsonl(tasks: Iterable[dict[str, Any]], output_path: Path) -> int:
    """Write tasks to JSONL and return the number written."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
            count += 1
    return count


def import_gsm8k(
    input_path: Path | str,
    output_path: Path | str,
    limit: int | None,
    force: bool,
) -> int:
    """Import a local GSM8K-style JSONL file into harness task JSONL."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    ensure_can_write(input_path, output_path, limit, force)

    def _converted_tasks() -> Iterable[dict[str, Any]]:
        written = 0
        for record_index, record in read_jsonl(input_path):
            if limit is not None and written >= limit:
                break
            yield convert_gsm8k_record(record, record_index, input_path)
            written += 1

    return write_tasks_jsonl(_converted_tasks(), output_path)


def read_mmlu_records(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    """Yield MMLU records from CSV or JSONL input."""
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for record_index, row in enumerate(reader):
                yield record_index, dict(row)
        return

    yield from read_jsonl(path)


def _mmlu_choices(record: dict[str, Any]) -> list[str]:
    choices = record.get("choices")
    if isinstance(choices, list) and len(choices) >= 4:
        return [str(choice) for choice in choices[:4]]
    return [str(record.get(letter, "")).strip() for letter in OPTION_LETTERS]


def _mmlu_answer_letter(answer: Any) -> str:
    if isinstance(answer, int):
        if 0 <= answer < len(OPTION_LETTERS):
            return OPTION_LETTERS[answer]
        if 1 <= answer <= len(OPTION_LETTERS):
            return OPTION_LETTERS[answer - 1]

    text = str(answer).strip()
    if text.upper() in OPTION_LETTERS:
        return text.upper()
    if text.isdigit():
        return _mmlu_answer_letter(int(text))
    raise ValueError(f"Unsupported MMLU answer value: {answer!r}")


def convert_mmlu_record(
    record: dict[str, Any],
    record_index: int,
    source_path: Path,
) -> dict[str, Any]:
    """Convert one MMLU-style record to this harness's task format."""
    question = record.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"{source_path}: record {record_index} has no question")

    choices = _mmlu_choices(record)
    if len(choices) < 4 or any(not choice for choice in choices[:4]):
        raise ValueError(f"{source_path}: record {record_index} must have A-D choices")

    answer = _mmlu_answer_letter(record.get("answer"))
    options_text = "\n".join(
        f"{letter}. {choice}" for letter, choice in zip(OPTION_LETTERS, choices)
    )
    metadata = {
        "category": "text",
        **source_metadata("mmlu", source_path, record_index),
    }
    if record.get("subject"):
        metadata["subject"] = str(record["subject"])

    return {
        "id": f"mmlu_{record_index + 1:06d}",
        "description": (
            f"{question.strip()}\n\n{options_text}\n\n"
            "Reply with only the correct option letter."
        ),
        "command": "noop",
        "expected_output": answer,
        "metadata": metadata,
    }


def import_mmlu(
    input_path: Path | str,
    output_path: Path | str,
    limit: int | None,
    force: bool,
) -> int:
    """Import a local MMLU CSV or JSONL file into harness task JSONL."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    ensure_can_write(input_path, output_path, limit, force)

    def _converted_tasks() -> Iterable[dict[str, Any]]:
        written = 0
        for record_index, record in read_mmlu_records(input_path):
            if limit is not None and written >= limit:
                break
            yield convert_mmlu_record(record, record_index, input_path)
            written += 1

    return write_tasks_jsonl(_converted_tasks(), output_path)


def convert_mbpp_record(
    record: dict[str, Any],
    record_index: int,
    source_path: Path,
) -> dict[str, Any]:
    """Convert one MBPP-style record to this harness's task format."""
    prompt = record.get("text") or record.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"{source_path}: record {record_index} has no text prompt")

    source_task_id = record.get("task_id", record_index + 1)
    tests = record.get("test_list") or record.get("tests") or []
    if isinstance(tests, str):
        tests = [tests]
    if not isinstance(tests, list):
        raise ValueError(f"{source_path}: record {record_index} tests must be a list")

    tests_text = "\n".join(str(test) for test in tests)
    description = (
        f"{prompt.strip()}\n\nProvided tests:\n{tests_text}\n\n"
        "Return only Python code."
    )
    return {
        "id": f"mbpp_{clean_id_part(source_task_id)}",
        "description": description,
        "command": "noop",
        "expected_output": "Pass provided tests",
        "metadata": {
            "category": "code",
            "artifact_kind": "misc",
            "artifact_extension": ".py",
            "source_task_id": source_task_id,
            "test_list": [str(test) for test in tests],
            **source_metadata("mbpp", source_path, record_index),
        },
    }


def import_mbpp(
    input_path: Path | str,
    output_path: Path | str,
    limit: int | None,
    force: bool,
) -> int:
    """Import a local MBPP-style JSONL file into harness task JSONL."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    ensure_can_write(input_path, output_path, limit, force)

    def _converted_tasks() -> Iterable[dict[str, Any]]:
        written = 0
        for record_index, record in read_jsonl(input_path):
            if limit is not None and written >= limit:
                break
            yield convert_mbpp_record(record, record_index, input_path)
            written += 1

    return write_tasks_jsonl(_converted_tasks(), output_path)


def convert_humaneval_record(
    record: dict[str, Any],
    record_index: int,
    source_path: Path,
) -> dict[str, Any]:
    """Convert one HumanEval-style record to this harness's task format."""
    prompt = record.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"{source_path}: record {record_index} has no prompt")

    source_task_id = record.get("task_id", record_index + 1)
    test = record.get("test", "")
    entry_point = record.get("entry_point", "")
    description = (
        "Complete the following Python function.\n\n"
        f"{prompt.rstrip()}\n\nProvided tests:\n{str(test).strip()}\n\n"
        "Return only Python code."
    )
    return {
        "id": f"humaneval_{clean_id_part(source_task_id).removeprefix('humaneval_')}",
        "description": description,
        "command": "noop",
        "expected_output": "Pass provided tests",
        "metadata": {
            "category": "code",
            "artifact_kind": "misc",
            "artifact_extension": ".py",
            "source_task_id": source_task_id,
            "entry_point": str(entry_point),
            "test": str(test),
            **source_metadata("humaneval", source_path, record_index),
        },
    }


def import_humaneval(
    input_path: Path | str,
    output_path: Path | str,
    limit: int | None,
    force: bool,
) -> int:
    """Import a local HumanEval-style JSONL file into harness task JSONL."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    ensure_can_write(input_path, output_path, limit, force)

    def _converted_tasks() -> Iterable[dict[str, Any]]:
        written = 0
        for record_index, record in read_jsonl(input_path):
            if limit is not None and written >= limit:
                break
            yield convert_humaneval_record(record, record_index, input_path)
            written += 1

    return write_tasks_jsonl(_converted_tasks(), output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import official/open-source benchmark data into harness JSONL."
    )
    parser.add_argument(
        "--source",
        choices=SUPPORTED_SOURCES,
        required=True,
        help="Source benchmark format to import.",
    )
    parser.add_argument(
        "--input",
        help="Path to a local source dataset file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of tasks to import.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Destination JSONL task file.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output if it already exists.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input:
        parser.exit(2, f"error: {INPUT_HELP[args.source]}\n")

    try:
        if args.source == "gsm8k":
            written = import_gsm8k(
                Path(args.input),
                Path(args.output),
                limit=args.limit,
                force=args.force,
            )
        elif args.source == "mmlu":
            written = import_mmlu(
                Path(args.input),
                Path(args.output),
                limit=args.limit,
                force=args.force,
            )
        elif args.source == "mbpp":
            written = import_mbpp(
                Path(args.input),
                Path(args.output),
                limit=args.limit,
                force=args.force,
            )
        elif args.source == "humaneval":
            written = import_humaneval(
                Path(args.input),
                Path(args.output),
                limit=args.limit,
                force=args.force,
            )
        else:
            parser.error(f"Unsupported source: {args.source}")
            return
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Imported {written} tasks to {args.output}")


if __name__ == "__main__":
    main()

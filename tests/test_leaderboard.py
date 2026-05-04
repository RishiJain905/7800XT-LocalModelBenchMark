"""Unit tests for runners/leaderboard.py.

Tests cover the generate_leaderboard function in isolation, using temporary
files and monkeypatching to avoid touching the real filesystem.
"""

from __future__ import annotations

import os

import pytest

from runners.leaderboard import generate_leaderboard


# ---------------------------------------------------------------------------
# generate_leaderboard
# ---------------------------------------------------------------------------


class TestGenerateLeaderboard:
    """Markdown leaderboard generation from benchmark summary CSV."""

    def test_creates_leaderboard_from_summary_csv(self, monkeypatch, tmp_path):
        """Two rows are sorted by avg_score descending and rendered correctly."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            "run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,"
            "pass_rate,average_score,average_latency_sec,repeats\n"
            "2026-05-01_19-56-53,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,10,9,1,0.9000,0.9000,1.420,1\n"
            "2026-05-01_19-56-53,qwen-18b-iq4-4k,tasks/math/basic_math.jsonl,"
            "10,10,10,0,1.0000,0.9500,2.880,1\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        generate_leaderboard(str(summary_path), str(output_path))

        assert output_path.exists()
        lines = output_path.read_text(encoding="utf-8").strip().split("\n")

        assert lines[0] == "# Local Model Benchmark Leaderboard"
        assert lines[2] == "## tasks/math/basic_math.jsonl"
        assert (
            lines[4]
            == "| Model Config | Suite | Task File | Status | Total Attempts | Pass Rate | Avg Score | Avg Latency |"
        )
        assert lines[5] == "|---|---|---|---|---:|---:|---:|---:|"

        # Sorted by avg_score desc: qwen-18b-iq4-4k (0.95) before qwen-9b-q8-4k (0.90)
        assert "qwen-18b-iq4-4k" in lines[6]
        assert "qwen-9b-q8-4k" in lines[7]

        # Verify formatting in the first data row (higher scorer)
        parts = lines[6].split("|")
        assert "100.0%" in parts[6]
        assert "0.95" in parts[7]
        assert "2.88s" in parts[8]

        # Verify formatting in the second data row
        parts = lines[7].split("|")
        assert "90.0%" in parts[6]
        assert "0.90" in parts[7]
        assert "1.42s" in parts[8]

    def test_sorting_by_score_then_pass_rate_then_latency(self, monkeypatch, tmp_path):
        """4 rows verify multi-key sorting: score desc, pass_rate desc, latency asc."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        # Row C: lowest score (0.90) but full pass rate
        # Row A: same score as C (0.90) but lower pass rate (0.60)
        # Row D: same score+pass_rate as B (0.95, 1.0) but lower latency (1.5 vs 3.0)
        # Row B: same score+pass_rate as D (0.95, 1.0) but higher latency (3.0)
        rows = [
            (
                "run-1",
                "model-A",
                "tasks/t.jsonl",
                "5",
                "5",
                "3",
                "2",
                "0.6000",
                "0.9000",
                "2.000",
                "1",
            ),
            (
                "run-1",
                "model-B",
                "tasks/t.jsonl",
                "5",
                "5",
                "5",
                "0",
                "1.0000",
                "0.9500",
                "3.000",
                "1",
            ),
            (
                "run-1",
                "model-C",
                "tasks/t.jsonl",
                "5",
                "5",
                "5",
                "0",
                "1.0000",
                "0.9000",
                "1.000",
                "1",
            ),
            (
                "run-1",
                "model-D",
                "tasks/t.jsonl",
                "5",
                "5",
                "5",
                "0",
                "1.0000",
                "0.9500",
                "1.500",
                "1",
            ),
        ]
        csv_lines = [
            "run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,pass_rate,average_score,average_latency_sec,repeats",
        ]
        for r in rows:
            csv_lines.append(",".join(r))
        summary_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

        output_path = tmp_path / "results" / "reports" / "leaderboard.md"
        generate_leaderboard(str(summary_path), str(output_path))

        lines = output_path.read_text(encoding="utf-8").strip().split("\n")
        data_rows = [ln for ln in lines if ln.startswith("| model-")]
        assert len(data_rows) == 4

        # Expected order:
        #   D (0.95, 1.0, 1.5) - lower latency wins tie-break over B
        #   B (0.95, 1.0, 3.0)
        #   C (0.90, 1.0, 1.0) - higher pass rate wins tie-break over A
        #   A (0.90, 0.6, 2.0)
        assert "model-D" in data_rows[0]
        assert "model-B" in data_rows[1]
        assert "model-C" in data_rows[2]
        assert "model-A" in data_rows[3]

    def test_suite_rows_are_grouped_and_sorted_independently(
        self, monkeypatch, tmp_path
    ):
        """Different suites render as separate groups with in-suite ranking."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,"
            "pass_rate,average_score,average_latency_sec,repeats,suite_id,suite_name,"
            "run_folder,status,started_at,completed_at,artifact_count"
        )
        rows = [
            "run-1,math-slower,benchmarks/reasoning/math.jsonl,5,5,5,0,1.0000,0.9000,4.000,1,reasoning.math,Math,,completed,,,0",
            "run-1,math-faster,benchmarks/reasoning/math.jsonl,5,5,5,0,1.0000,0.9000,1.000,1,reasoning.math,Math,,completed,,,0",
            "run-1,code-model,benchmarks/coding/frontend.jsonl,5,5,4,1,0.8000,0.8000,2.000,1,coding.frontend,Frontend Coding,,completed,,,2",
        ]
        summary_path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")

        output_path = tmp_path / "results" / "reports" / "leaderboard.md"
        generate_leaderboard(str(summary_path), str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert "## reasoning.math (Math)" in content
        assert "## coding.frontend (Frontend Coding)" in content

        lines = content.strip().split("\n")
        data_rows = [ln for ln in lines if ln.startswith("| math-")]
        assert "math-faster" in data_rows[0]
        assert "math-slower" in data_rows[1]

    def test_deduplication_keeps_most_recent_run(self, monkeypatch, tmp_path):
        """Same (model_config_id, task_file) pair keeps the lexicographically larger run_id."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            "run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,"
            "pass_rate,average_score,average_latency_sec,repeats\n"
            "2026-05-01_19-56-53,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,10,5,5,0.5000,0.5000,1.000,1\n"
            "2026-05-01_20-00-00,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,10,9,1,0.9000,0.9000,1.420,1\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        generate_leaderboard(str(summary_path), str(output_path))

        lines = output_path.read_text(encoding="utf-8").strip().split("\n")
        data_rows = [ln for ln in lines if ln.startswith("| qwen-")]
        assert len(data_rows) == 1
        assert "90.0%" in data_rows[0]
        assert "0.90" in data_rows[0]
        assert "1.42s" in data_rows[0]

    def test_deduplication_keeps_latest_run_per_model_suite(
        self, monkeypatch, tmp_path
    ):
        """Task 16 rows dedupe by model_config_id and suite_id."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            "run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,"
            "pass_rate,average_score,average_latency_sec,repeats,suite_id,suite_name,"
            "run_folder,status,started_at,completed_at,artifact_count\n"
            "2026-05-01_19-56-53,model-a,benchmarks/reasoning/math.jsonl,"
            "10,10,5,5,0.5000,0.5000,1.000,1,reasoning.math,Math,,completed,,,0\n"
            "2026-05-01_20-00-00,model-a,benchmarks/reasoning/math_v2.jsonl,"
            "10,10,9,1,0.9000,0.9000,1.420,1,reasoning.math,Math,,completed,,,0\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        generate_leaderboard(str(summary_path), str(output_path))

        data_rows = [
            ln
            for ln in output_path.read_text(encoding="utf-8").splitlines()
            if ln.startswith("| model-a")
        ]
        assert len(data_rows) == 1
        assert "math_v2.jsonl" in data_rows[0]
        assert "90.0%" in data_rows[0]

    def test_empty_csv(self, monkeypatch, tmp_path):
        """CSV with header only produces a 'No data yet.' leaderboard."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            "run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,"
            "pass_rate,average_score,average_latency_sec,repeats\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        generate_leaderboard(str(summary_path), str(output_path))

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "No data yet." in content

    def test_missing_csv_file(self, monkeypatch, tmp_path, capsys):
        """Missing CSV still writes an empty leaderboard and prints a warning to stderr."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        generate_leaderboard(str(summary_path), str(output_path))

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "No data yet." in content

        captured = capsys.readouterr()
        assert "WARNING: Summary CSV not found" in captured.err

    def test_returns_absolute_path(self, monkeypatch, tmp_path):
        """The function returns an absolute path string."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            "run_id,model_config_id,task_file,total_tasks,total_attempts,passed,failed,"
            "pass_rate,average_score,average_latency_sec,repeats\n"
            "2026-05-01_19-56-53,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,10,9,1,0.9000,0.9000,1.420,1\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        result = generate_leaderboard(str(summary_path), str(output_path))

        assert os.path.isabs(result)

    def test_old_format_csv_still_works(self, monkeypatch, tmp_path):
        """CSV missing total_attempts and repeats columns defaults gracefully."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        # Old format: no total_attempts or repeats columns
        summary_path.write_text(
            "run_id,model_config_id,task_file,total_tasks,passed,failed,"
            "pass_rate,average_score,average_latency_sec\n"
            "2026-05-01_19-56-53,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,9,1,0.9000,0.9000,1.420\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        generate_leaderboard(str(summary_path), str(output_path))

        assert output_path.exists()
        lines = output_path.read_text(encoding="utf-8").strip().split("\n")
        assert lines[2] == "## tasks/math/basic_math.jsonl"
        data_rows = [ln for ln in lines if ln.startswith("| qwen-")]
        assert len(data_rows) == 1
        # total_attempts defaults to total_tasks (10), repeats defaults to 1
        assert "10" in data_rows[0]
        assert "1" in data_rows[0]
        assert "90.0%" in data_rows[0]
        assert "0.90" in data_rows[0]
        assert "1.42s" in data_rows[0]

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
            "run_id,model_config_id,task_file,total_tasks,passed,failed,"
            "pass_rate,average_score,average_latency_sec\n"
            "2026-05-01_19-56-53,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,9,1,0.9000,0.9000,1.420\n"
            "2026-05-01_19-56-53,qwen-18b-iq4-4k,tasks/math/basic_math.jsonl,"
            "10,10,0,1.0000,0.9500,2.880\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        generate_leaderboard(str(summary_path), str(output_path))

        assert output_path.exists()
        lines = output_path.read_text(encoding="utf-8").strip().split("\n")

        assert lines[0] == "# Local Model Benchmark Leaderboard"
        assert (
            lines[2]
            == "| Model Config | Task File | Total Tasks | Pass Rate | Avg Score | Avg Latency |"
        )
        assert lines[3] == "|---|---:|---:|---:|---:|---:|"

        # Sorted by avg_score desc: qwen-18b-iq4-4k (0.95) before qwen-9b-q8-4k (0.90)
        assert "qwen-18b-iq4-4k" in lines[4]
        assert "qwen-9b-q8-4k" in lines[5]

        # Verify formatting in the first data row (higher scorer)
        parts = lines[4].split("|")
        assert "100.0%" in parts[4]
        assert "0.95" in parts[5]
        assert "2.88s" in parts[6]

        # Verify formatting in the second data row
        parts = lines[5].split("|")
        assert "90.0%" in parts[4]
        assert "0.90" in parts[5]
        assert "1.42s" in parts[6]

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
                "3",
                "2",
                "0.6000",
                "0.9000",
                "2.000",
            ),
            (
                "run-1",
                "model-B",
                "tasks/t.jsonl",
                "5",
                "5",
                "0",
                "1.0000",
                "0.9500",
                "3.000",
            ),
            (
                "run-1",
                "model-C",
                "tasks/t.jsonl",
                "5",
                "5",
                "0",
                "1.0000",
                "0.9000",
                "1.000",
            ),
            (
                "run-1",
                "model-D",
                "tasks/t.jsonl",
                "5",
                "5",
                "0",
                "1.0000",
                "0.9500",
                "1.500",
            ),
        ]
        csv_lines = [
            "run_id,model_config_id,task_file,total_tasks,passed,failed,pass_rate,average_score,average_latency_sec",
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

    def test_deduplication_keeps_most_recent_run(self, monkeypatch, tmp_path):
        """Same (model_config_id, task_file) pair keeps the lexicographically larger run_id."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            "run_id,model_config_id,task_file,total_tasks,passed,failed,"
            "pass_rate,average_score,average_latency_sec\n"
            "2026-05-01_19-56-53,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,5,5,0.5000,0.5000,1.000\n"
            "2026-05-01_20-00-00,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,9,1,0.9000,0.9000,1.420\n",
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

    def test_empty_csv(self, monkeypatch, tmp_path):
        """CSV with header only produces a 'No data yet.' leaderboard."""
        monkeypatch.chdir(tmp_path)
        summary_path = tmp_path / "results" / "summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            "run_id,model_config_id,task_file,total_tasks,passed,failed,"
            "pass_rate,average_score,average_latency_sec\n",
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
            "run_id,model_config_id,task_file,total_tasks,passed,failed,"
            "pass_rate,average_score,average_latency_sec\n"
            "2026-05-01_19-56-53,qwen-9b-q8-4k,tasks/math/basic_math.jsonl,"
            "10,9,1,0.9000,0.9000,1.420\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "results" / "reports" / "leaderboard.md"

        result = generate_leaderboard(str(summary_path), str(output_path))

        assert os.path.isabs(result)

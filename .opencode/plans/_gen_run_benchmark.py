import sys, base64, os

target = sys.argv[1]

# Build content safely - single lines, no escaping issues in source
# This approach avoids ALL quoting conflicts
lines = """""".split(chr(10))

# Use a helper to build the content cleanly
def build():
    L = []
    L.append("""Local Model Benchmark Harness - orchestrates config loading, model prompting,""")
    L.append("and scoring across a JSONL task file to produce per-task results and a summary.")
    L.append("Supports direct task files (--task-file) or named benchmark suites (--suite).")
    L.append('""'")
    L.append("")
    L.append("from __future__ import annotations")
    L.append("")
    L.append("import argparse")
    L.append("import sys")
    L.append("from datetime import datetime")
    L.append("import uuid")
    L.append("from typing import Any")
    L.append("")
    L.append("from runners.config_loader import load_config")
    L.append("from runners.llama_client import run_prompt")
    L.append("from runners.leaderboard import generate_leaderboard")
    L.append("from runners.result_writer import append_summary, write_raw_results")
    L.append("from runners.task_loader import load_tasks")
    L.append("from runners.suite_registry import get_suite")
    L.append("from scorers.registry import get_scorer")
    L.append("")
    return L

content = chr(10).join(build()) + chr(10)
with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print("Written:", target, len(content), "chars")

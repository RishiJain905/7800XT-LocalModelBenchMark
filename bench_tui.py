"""Keyboard-driven terminal UI for local model benchmark runs."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, DataTable, Footer, Input, Label, ListItem, ListView, Log, Static

from runners.benchmark_runner import BenchmarkCancelled, run_benchmark
from runners.config_loader import load_config
from runners.leaderboard import generate_leaderboard
from runners.model_registry import get_model_config, list_model_configs
from runners.result_writer import (
    append_run_raw_result,
    append_summary,
    build_manifest,
    create_run_folder,
    update_manifest_status,
    write_manifest,
    write_run_raw_results,
    write_run_summary,
)
from runners.resume import (
    completed_attempt_key,
    list_resumable_runs,
    load_resume_state,
)
from runners.server_health import check_server
from runners.suite_registry import list_suites
from runners.task_loader import load_tasks


RESUMABLE_STATUSES = {"running", "cancelled", "failed"}


@dataclass(frozen=True)
class RunSettings:
    repeats: int = 1
    max_tasks: int | None = None


@dataclass(frozen=True)
class TuiRunOutcome:
    status: str
    run_dir: Path
    run_id: str
    summary: dict[str, Any]
    results: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResultRunRecord:
    run_dir: Path
    run_id: str
    model_config_id: str
    suite_label: str
    task_file: str
    status: str
    started_at: str
    manifest: dict[str, Any]
    summary: dict[str, Any]

    @property
    def is_resumable(self) -> bool:
        return self.status in RESUMABLE_STATUSES


ProgressCallback = Callable[[dict[str, Any]], None]
CancelCallback = Callable[[], bool]


def validate_run_settings(repeats_text: str, max_tasks_text: str) -> tuple[int, int | None]:
    """Parse and validate run settings from TUI inputs."""
    try:
        repeats = int(repeats_text.strip())
    except ValueError as exc:
        raise ValueError("Repeats must be a positive integer.") from exc
    if repeats <= 0:
        raise ValueError("Repeats must be greater than zero.")

    stripped_max_tasks = max_tasks_text.strip()
    if not stripped_max_tasks:
        return repeats, None

    try:
        max_tasks = int(stripped_max_tasks)
    except ValueError as exc:
        raise ValueError("Max tasks must be blank or a positive integer.") from exc
    if max_tasks <= 0:
        raise ValueError("Max tasks must be greater than zero when provided.")
    return repeats, max_tasks


def discover_result_runs(results_root: str | Path = "results/runs") -> list[ResultRunRecord]:
    """Return manifest-backed benchmark run records for the results browser."""
    root = Path(results_root)
    if not root.exists():
        return []

    records: list[ResultRunRecord] = []
    for manifest_path in root.glob("*/*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(manifest, dict):
            continue

        summary_path = manifest_path.parent / "summary.json"
        summary: dict[str, Any] = {}
        if summary_path.is_file() and summary_path.stat().st_size:
            try:
                summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
                if isinstance(summary_data, dict):
                    summary = summary_data
            except (OSError, json.JSONDecodeError):
                summary = {}

        suite_label = (
            str(manifest.get("suite_id") or "")
            or str(manifest.get("suite_name") or "")
            or str(manifest.get("task_file") or "")
        )
        run_dir = manifest_path.parent.resolve()
        records.append(
            ResultRunRecord(
                run_dir=run_dir,
                run_id=str(manifest.get("run_id") or run_dir.name),
                model_config_id=str(manifest.get("model_config_id") or run_dir.parent.name),
                suite_label=suite_label,
                task_file=str(manifest.get("task_file") or ""),
                status=str(manifest.get("status") or ""),
                started_at=str(manifest.get("started_at") or ""),
                manifest=manifest,
                summary=summary,
            )
        )

    return sorted(records, key=lambda record: record.started_at, reverse=True)


def _build_summary_from_results(
    results: list[dict[str, Any]],
    run_id: str,
    total_tasks: int,
    total_attempts: int,
) -> dict[str, Any]:
    completed_attempts = len(results)
    passed = sum(1 for result in results if result["passed"])
    failed = completed_attempts - passed
    return {
        "results": results,
        "run_id": run_id,
        "total_tasks": total_tasks,
        "total_attempts": total_attempts,
        "passed": passed,
        "failed": failed,
        "average_score": (
            sum(result["score"] for result in results) / completed_attempts
            if completed_attempts
            else 0.0
        ),
        "average_latency_sec": (
            sum(result["latency_sec"] for result in results) / completed_attempts
            if completed_attempts
            else 0.0
        ),
    }


def _artifact_count(results: list[dict[str, Any]]) -> int:
    return sum(len(result.get("artifact_paths") or []) for result in results)


def _enrich_run_summary(
    run_dir: str | Path,
    *,
    status: str,
    started_at: str | None,
    completed_at: str | None,
    artifact_count: int,
) -> None:
    summary_path = Path(run_dir) / "summary.json"
    if not summary_path.is_file() or not summary_path.stat().st_size:
        return
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return
    payload["status"] = status
    payload["started_at"] = started_at
    payload["completed_at"] = completed_at
    payload["artifact_count"] = artifact_count
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{uuid.uuid4().hex[:8]}"


def execute_suite_run(
    config: dict[str, Any],
    suite: dict[str, Any],
    settings: RunSettings,
    *,
    progress_callback: ProgressCallback | None = None,
    cancel_callback: CancelCallback | None = None,
) -> TuiRunOutcome:
    """Execute one suite from the TUI and persist structured results."""
    task_file = str(suite["task_file"])
    tasks = load_tasks(task_file)
    if settings.max_tasks is not None:
        tasks = tasks[: settings.max_tasks]
    if not tasks:
        raise ValueError(f"Suite '{suite['id']}' has no tasks to run.")

    run_id = _build_run_id()
    run_dir = create_run_folder(config["id"], run_id)
    started_at = datetime.now().isoformat(timespec="seconds")
    total_attempts = len(tasks) * settings.repeats
    suite_info = {"id": suite["id"], "name": suite.get("name", "")}

    manifest = build_manifest(
        config,
        task_file,
        run_id,
        "running",
        started_at,
        suite_info=suite_info,
    )
    manifest["repeats"] = settings.repeats
    manifest["total_tasks"] = len(tasks)
    manifest["total_attempts"] = total_attempts
    write_manifest(run_dir, manifest)

    completed_results: list[dict[str, Any]] = []

    def record_result(result: dict[str, Any]) -> None:
        completed_results.append(result)
        append_run_raw_result(run_dir, result)
        if progress_callback:
            progress_callback(
                {
                    "type": "result",
                    "run_dir": str(run_dir),
                    "suite_id": suite["id"],
                    "completed": len(completed_results),
                    "total": total_attempts,
                    "result": result,
                }
            )

    def record_progress(completed: int, total: int) -> None:
        if progress_callback:
            progress_callback(
                {
                    "type": "progress",
                    "run_dir": str(run_dir),
                    "suite_id": suite["id"],
                    "completed": completed,
                    "total": total,
                }
            )

    options: dict[str, Any] = {
        "repeats": settings.repeats,
        "dry_run": False,
        "task_file": task_file,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "suite_id": suite["id"],
        "suite_name": suite.get("name", ""),
    }

    try:
        summary = run_benchmark(
            config,
            tasks,
            options,
            progress_callback=record_progress,
            result_callback=record_result,
            cancel_callback=cancel_callback,
        )
    except (KeyboardInterrupt, BenchmarkCancelled):
        completed_at = datetime.now().isoformat(timespec="seconds")
        summary = _build_summary_from_results(
            completed_results,
            run_id,
            len(tasks),
            total_attempts,
        )
        write_run_summary(
            run_dir,
            summary,
            config,
            task_file,
            "cancelled",
            repeats=settings.repeats,
            suite_info=suite_info,
        )
        _enrich_run_summary(
            run_dir,
            status="cancelled",
            started_at=started_at,
            completed_at=completed_at,
            artifact_count=_artifact_count(completed_results),
        )
        update_manifest_status(run_dir, "cancelled", completed_at)
        return TuiRunOutcome("cancelled", run_dir, run_id, summary, completed_results)
    except Exception:
        completed_at = datetime.now().isoformat(timespec="seconds")
        summary = _build_summary_from_results(
            completed_results,
            run_id,
            len(tasks),
            total_attempts,
        )
        write_run_summary(
            run_dir,
            summary,
            config,
            task_file,
            "failed",
            repeats=settings.repeats,
            suite_info=suite_info,
        )
        _enrich_run_summary(
            run_dir,
            status="failed",
            started_at=started_at,
            completed_at=completed_at,
            artifact_count=_artifact_count(completed_results),
        )
        update_manifest_status(run_dir, "failed", completed_at)
        raise

    flat_results = summary["results"]
    completed_at = datetime.now().isoformat(timespec="seconds")
    write_run_raw_results(run_dir, flat_results)
    write_run_summary(
        run_dir,
        summary,
        config,
        task_file,
        "completed",
        repeats=settings.repeats,
        suite_info=suite_info,
    )
    _enrich_run_summary(
        run_dir,
        status="completed",
        started_at=started_at,
        completed_at=completed_at,
        artifact_count=_artifact_count(flat_results),
    )
    update_manifest_status(run_dir, "completed", completed_at)
    append_summary(
        flat_results,
        config["id"],
        task_file,
        run_id,
        repeats=settings.repeats,
        total_tasks=summary["total_tasks"],
    )
    generate_leaderboard()
    return TuiRunOutcome("completed", run_dir, run_id, summary, flat_results)


def _load_resume_config(manifest: dict[str, Any]) -> dict[str, Any]:
    config_id = str(manifest["model_config_id"])
    config_path = Path("configs") / "models" / f"{config_id}.yaml"
    if config_path.is_file():
        return load_config(str(config_path))
    return {
        "id": config_id,
        "model_name": manifest.get("model_name", ""),
        "runtime": {"server_url": manifest.get("server_url", "")},
        "settings": manifest.get("settings", {}),
    }


def execute_resume_run(
    run_dir: str | Path,
    *,
    progress_callback: ProgressCallback | None = None,
    cancel_callback: CancelCallback | None = None,
) -> TuiRunOutcome:
    """Resume an incomplete run folder from the TUI."""
    state = load_resume_state(run_dir)
    config = _load_resume_config(state.manifest)
    completed_results = [
        result for result in state.completed_results if completed_attempt_key(result)
    ]
    suite_info = state.suite_info or {"id": "", "name": ""}
    suite_id = suite_info.get("id", "")
    started_at = str(state.manifest.get("started_at") or "")
    new_results: list[dict[str, Any]] = []

    def record_result(result: dict[str, Any]) -> None:
        new_results.append(result)
        append_run_raw_result(state.run_dir, result)
        if progress_callback:
            progress_callback(
                {
                    "type": "result",
                    "run_dir": str(state.run_dir),
                    "suite_id": suite_id,
                    "completed": len(state.completed_attempts) + len(new_results),
                    "total": state.total_attempts,
                    "result": result,
                }
            )

    def record_progress(completed: int, total: int) -> None:
        if progress_callback:
            progress_callback(
                {
                    "type": "progress",
                    "run_dir": str(state.run_dir),
                    "suite_id": suite_id,
                    "completed": completed,
                    "total": total,
                }
            )

    options: dict[str, Any] = {
        "repeats": state.repeats,
        "dry_run": False,
        "task_file": state.manifest["task_file"],
        "run_id": state.manifest["run_id"],
        "run_dir": str(state.run_dir),
        "skip_attempts": state.completed_attempts,
        "suite_id": suite_id,
        "suite_name": suite_info.get("name", ""),
    }

    update_manifest_status(state.run_dir, "running")
    try:
        run_benchmark(
            config,
            state.tasks,
            options,
            progress_callback=record_progress,
            result_callback=record_result,
            cancel_callback=cancel_callback,
        )
    except (KeyboardInterrupt, BenchmarkCancelled):
        completed_at = datetime.now().isoformat(timespec="seconds")
        combined = completed_results + new_results
        summary = _build_summary_from_results(
            combined,
            state.manifest["run_id"],
            len(state.tasks),
            state.total_attempts,
        )
        write_run_summary(
            state.run_dir,
            summary,
            config,
            state.manifest["task_file"],
            "cancelled",
            repeats=state.repeats,
            suite_info=suite_info,
        )
        _enrich_run_summary(
            state.run_dir,
            status="cancelled",
            started_at=started_at,
            completed_at=completed_at,
            artifact_count=_artifact_count(combined),
        )
        update_manifest_status(state.run_dir, "cancelled", completed_at)
        return TuiRunOutcome(
            "cancelled",
            state.run_dir,
            state.manifest["run_id"],
            summary,
            combined,
            state.warnings,
        )

    combined = completed_results + new_results
    summary = _build_summary_from_results(
        combined,
        state.manifest["run_id"],
        len(state.tasks),
        state.total_attempts,
    )
    completed_at = datetime.now().isoformat(timespec="seconds")
    write_run_summary(
        state.run_dir,
        summary,
        config,
        state.manifest["task_file"],
        "completed",
        repeats=state.repeats,
        suite_info=suite_info,
    )
    _enrich_run_summary(
        state.run_dir,
        status="completed",
        started_at=started_at,
        completed_at=completed_at,
        artifact_count=_artifact_count(combined),
    )
    update_manifest_status(state.run_dir, "completed", completed_at)
    append_summary(
        combined,
        config["id"],
        state.manifest["task_file"],
        state.manifest["run_id"],
        repeats=state.repeats,
        total_tasks=summary["total_tasks"],
    )
    generate_leaderboard()
    return TuiRunOutcome(
        "completed",
        state.run_dir,
        state.manifest["run_id"],
        summary,
        combined,
        state.warnings,
    )


class DashboardScreen(Screen):
    BINDINGS = [
        ("m", "models", "Models"),
        ("s", "suites", "Suites"),
        ("o", "settings", "Settings"),
        ("h", "health", "Health"),
        ("enter", "run", "Run"),
        ("b", "results", "Results"),
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="dashboard"):
            yield Static("Local Model Benchmark", id="title")
            yield Static("", id="status")
            with Horizontal():
                yield Button("Models", id="models")
                yield Button("Suites", id="suites")
                yield Button("Settings", id="settings")
                yield Button("Check Health", id="health")
                yield Button("Run", id="run")
                yield Button("Results", id="results")
            yield Log(id="dashboard_log")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_status()

    def refresh_status(self) -> None:
        app = self.app
        model_label = app.selected_model.get("id", "none") if app.selected_model else "none"
        suite_count = len(app.selected_suites)
        health = "unknown"
        if app.server_health:
            health = "reachable" if app.server_health.get("reachable") else "unreachable"
        latest = app.latest_outcome.run_dir if app.latest_outcome else "none"
        errors = "; ".join(app.registry_errors) if app.registry_errors else "none"
        self.query_one("#status", Static).update(
            f"Model: {model_label}\n"
            f"Server: {health}\n"
            f"Selected suites: {suite_count}\n"
            f"Repeats: {app.run_settings.repeats}  Max tasks: {app.run_settings.max_tasks or 'all'}\n"
            f"Last run: {latest}\n"
            f"Registry errors: {errors}"
        )

    def on_screen_resume(self) -> None:
        self.refresh_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id or ""
        if action == "models":
            self.action_models()
        elif action == "suites":
            self.action_suites()
        elif action == "settings":
            self.action_settings()
        elif action == "health":
            self.action_health()
        elif action == "run":
            self.action_run()
        elif action == "results":
            self.action_results()

    def action_models(self) -> None:
        self.app.push_screen(ModelSelectionScreen())

    def action_suites(self) -> None:
        self.app.push_screen(SuiteSelectionScreen())

    def action_settings(self) -> None:
        self.app.push_screen(RunSettingsScreen())

    def action_results(self) -> None:
        self.app.push_screen(ResultsBrowserScreen())

    def action_health(self) -> None:
        self.app.refresh_health()
        self.refresh_status()

    def action_run(self) -> None:
        self.app.start_selected_run()


class ModelSelectionScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back"), ("enter", "select", "Select")]

    def compose(self) -> ComposeResult:
        yield Static("Select Model Config", id="title")
        yield ListView(id="model_list")
        yield Static("", id="model_detail")
        yield Footer()

    def on_mount(self) -> None:
        list_view = self.query_one("#model_list", ListView)
        list_view.clear()
        if not self.app.model_configs:
            list_view.append(ListItem(Label("No model configs found")))
            return
        for config in self.app.model_configs:
            label = f"{config['id']} - {config.get('model_name', '')}"
            item = ListItem(Label(label))
            item.config = config  # type: ignore[attr-defined]
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        config = getattr(event.item, "config", None)
        if config:
            self.app.selected_model = config
            self.app.server_health = None
            self.app.pop_screen()

    def action_select(self) -> None:
        list_view = self.query_one("#model_list", ListView)
        if list_view.highlighted_child is not None:
            list_view.action_select_cursor()


class SuiteSelectionScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("space", "toggle", "Toggle"),
        ("enter", "app.pop_screen", "Done"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Select Benchmark Suites", id="title")
        with Vertical(id="suite_checks"):
            pass
        yield Footer()

    def on_mount(self) -> None:
        container = self.query_one("#suite_checks", Vertical)
        selected = {suite["id"] for suite in self.app.selected_suites}
        for suite in self.app.suites:
            checkbox = Checkbox(
                f"{suite['id']} - {suite.get('name', '')}",
                value=suite["id"] in selected,
                id=f"suite-{suite['id'].replace('.', '-')}",
            )
            checkbox.suite = suite  # type: ignore[attr-defined]
            container.mount(checkbox)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        selected: list[dict[str, Any]] = []
        for checkbox in self.query(Checkbox):
            if checkbox.value:
                suite = getattr(checkbox, "suite", None)
                if suite:
                    selected.append(suite)
        self.app.selected_suites = selected

    def action_toggle(self) -> None:
        focused = self.focused
        if isinstance(focused, Checkbox):
            focused.value = not focused.value


class RunSettingsScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back"), ("enter", "save", "Save")]

    def compose(self) -> ComposeResult:
        yield Static("Run Settings", id="title")
        yield Label("Repeats")
        yield Input(str(self.app.run_settings.repeats), id="repeats")
        yield Label("Max tasks (blank for all)")
        yield Input("" if self.app.run_settings.max_tasks is None else str(self.app.run_settings.max_tasks), id="max_tasks")
        yield Static("", id="settings_error")
        yield Button("Save", id="save")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()

    def action_save(self) -> None:
        repeats_text = self.query_one("#repeats", Input).value
        max_tasks_text = self.query_one("#max_tasks", Input).value
        try:
            repeats, max_tasks = validate_run_settings(repeats_text, max_tasks_text)
        except ValueError as exc:
            self.query_one("#settings_error", Static).update(str(exc))
            return
        self.app.run_settings = RunSettings(repeats=repeats, max_tasks=max_tasks)
        self.app.pop_screen()


class RunProgressScreen(Screen):
    BINDINGS = [("c", "cancel", "Cancel"), ("escape", "dashboard", "Dashboard")]

    def compose(self) -> ComposeResult:
        yield Static("Run Progress", id="title")
        yield Static("Waiting to start...", id="progress_status")
        yield Log(id="run_log")
        yield Footer()

    def on_mount(self) -> None:
        self.app.progress_screen = self
        if (
            not self.app.smoke_test
            and self.app.run_worker is None
            and self.app.pending_resume_dir is None
        ):
            self.app.run_selected_suites_worker()

    def on_unmount(self) -> None:
        if self.app.progress_screen is self:
            self.app.progress_screen = None

    def log_event(self, message: str) -> None:
        self.query_one("#run_log", Log).write_line(message)

    def set_status(self, message: str) -> None:
        self.query_one("#progress_status", Static).update(message)

    def action_cancel(self) -> None:
        self.app.cancel_requested = True
        self.set_status("Cancellation requested. Waiting for current attempt to stop.")

    def action_dashboard(self) -> None:
        self.app.pop_screen()


class ResultsBrowserScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back"), ("r", "resume", "Resume")]

    def compose(self) -> ComposeResult:
        yield Static("Results Browser", id="title")
        yield DataTable(id="runs_table")
        yield Static("", id="run_detail")
        yield Footer()

    def on_mount(self) -> None:
        self.records = discover_result_runs()
        table = self.query_one("#runs_table", DataTable)
        table.add_columns("Run", "Model", "Suite", "Status", "Started")
        for record in self.records:
            table.add_row(
                record.run_id,
                record.model_config_id,
                record.suite_label,
                record.status,
                record.started_at,
                key=record.run_id,
            )
        if self.records:
            table.cursor_type = "row"
            table.move_cursor(row=0)
            self._show_record(self.records[0])
        else:
            self.query_one("#run_detail", Static).update("No runs found.")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        index = event.cursor_row
        if 0 <= index < len(self.records):
            self._show_record(self.records[index])

    def _show_record(self, record: ResultRunRecord) -> None:
        score = record.summary.get("average_score", "n/a")
        pass_rate = record.summary.get("pass_rate", "n/a")
        resumable = "yes" if record.is_resumable else "no"
        self.query_one("#run_detail", Static).update(
            f"Run folder: {record.run_dir}\n"
            f"Task file: {record.task_file}\n"
            f"Average score: {score}\n"
            f"Pass rate: {pass_rate}\n"
            f"Resumable: {resumable}"
        )

    def action_resume(self) -> None:
        table = self.query_one("#runs_table", DataTable)
        row = table.cursor_row
        if 0 <= row < len(self.records):
            record = self.records[row]
            if record.is_resumable:
                self.app.pending_resume_dir = record.run_dir
                self.app.push_screen(RunProgressScreen())
                self.app.resume_run_worker(record.run_dir)


class BenchmarkTuiApp(App):
    CSS = """
    Screen {
        padding: 1 2;
    }
    #title {
        text-style: bold;
        margin-bottom: 1;
    }
    Button {
        margin-right: 1;
    }
    #dashboard, #suite_checks {
        height: 100%;
    }
    #status, #model_detail, #settings_error, #run_detail, #progress_status {
        margin: 1 0;
    }
    Log {
        height: 1fr;
    }
    DataTable {
        height: 1fr;
    }
    """
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, *, smoke_test: bool = False) -> None:
        super().__init__()
        self.smoke_test = smoke_test
        self.model_configs: list[dict[str, Any]] = []
        self.suites: list[dict[str, Any]] = []
        self.registry_errors: list[str] = []
        self.selected_model: dict[str, Any] | None = None
        self.server_health: dict[str, Any] | None = None
        self.selected_suites: list[dict[str, Any]] = []
        self.run_settings = RunSettings()
        self.latest_result: dict[str, Any] | None = None
        self.latest_outcome: TuiRunOutcome | None = None
        self.cancel_requested = False
        self.progress_screen: RunProgressScreen | None = None
        self.run_worker = None
        self.pending_resume_dir: Path | None = None

    def compose(self) -> ComposeResult:
        return
        yield

    def on_mount(self) -> None:
        self.load_registries()
        self.push_screen(DashboardScreen())

    def load_registries(self) -> None:
        self.registry_errors = []
        try:
            self.model_configs = list_model_configs()
        except Exception as exc:
            self.model_configs = []
            self.registry_errors.append(f"Model registry: {exc}")

        try:
            self.suites = list_suites()
        except Exception as exc:
            self.suites = []
            self.registry_errors.append(f"Suite registry: {exc}")

        if self.selected_model is None and self.model_configs:
            self.selected_model = self.model_configs[0]
        if not self.selected_suites and self.suites:
            self.selected_suites = [self.suites[0]]

    def refresh_health(self) -> None:
        if not self.selected_model:
            self.server_health = {
                "reachable": False,
                "error": "No model config selected.",
            }
            return
        self.server_health = check_server(self.selected_model)

    def start_selected_run(self) -> None:
        if not self.selected_model:
            self.notify("Select a model config first.", severity="warning")
            return
        if not self.selected_suites:
            self.notify("Select at least one benchmark suite.", severity="warning")
            return
        if self.server_health is None:
            self.refresh_health()
        self.push_screen(RunProgressScreen())

    def _cancel_requested(self) -> bool:
        return self.cancel_requested

    def _post_progress(self, event: dict[str, Any]) -> None:
        self.call_from_thread(self.handle_progress_event, event)

    def handle_progress_event(self, event: dict[str, Any]) -> None:
        if event.get("type") == "result":
            result = event["result"]
            self.latest_result = result
            if self.progress_screen:
                self.progress_screen.log_event(
                    f"[{event['completed']}/{event['total']}] "
                    f"{result['task_id']} score={result['score']} "
                    f"latency={result['latency_sec']:.2f}s"
                )
        if self.progress_screen:
            self.progress_screen.set_status(
                f"{event.get('suite_id', '')}: "
                f"{event.get('completed', 0)}/{event.get('total', 0)} "
                f"Output: {event.get('run_dir', '')}"
            )

    @work(thread=True, exclusive=True, group="benchmark", exit_on_error=False)
    def run_selected_suites_worker(self) -> None:
        self.run_worker = True
        self.cancel_requested = False
        try:
            if not self.selected_model:
                raise ValueError("No model config selected.")
            for suite in self.selected_suites:
                if self.cancel_requested:
                    break
                self.call_from_thread(
                    self._progress_message,
                    f"Starting {suite['id']}...",
                )
                outcome = execute_suite_run(
                    self.selected_model,
                    suite,
                    self.run_settings,
                    progress_callback=self._post_progress,
                    cancel_callback=self._cancel_requested,
                )
                self.latest_outcome = outcome
                self.call_from_thread(
                    self._progress_message,
                    f"{suite['id']} {outcome.status}: {outcome.run_dir}",
                )
                if outcome.status != "completed":
                    break
        except Exception as exc:
            self.call_from_thread(self._progress_message, f"Run failed: {exc}")
        finally:
            self.call_from_thread(self._run_finished)

    @work(thread=True, exclusive=True, group="benchmark", exit_on_error=False)
    def resume_run_worker(self, run_dir: str | Path) -> None:
        self.run_worker = True
        self.cancel_requested = False
        try:
            outcome = execute_resume_run(
                run_dir,
                progress_callback=self._post_progress,
                cancel_callback=self._cancel_requested,
            )
            self.latest_outcome = outcome
            self.call_from_thread(
                self._progress_message,
                f"Resume {outcome.status}: {outcome.run_dir}",
            )
            for warning in outcome.warnings:
                self.call_from_thread(self._progress_message, f"WARNING: {warning}")
        except Exception as exc:
            self.call_from_thread(self._progress_message, f"Resume failed: {exc}")
        finally:
            self.call_from_thread(self._run_finished)

    def _progress_message(self, message: str) -> None:
        if self.progress_screen:
            self.progress_screen.log_event(message)
            self.progress_screen.set_status(message)

    def _run_finished(self) -> None:
        self.run_worker = None
        self.pending_resume_dir = None
        if self.progress_screen:
            self.progress_screen.log_event("Run worker finished.")


async def run_smoke_test() -> None:
    app = BenchmarkTuiApp(smoke_test=True)
    async with app.run_test():
        app.load_registries()
        app.push_screen(ModelSelectionScreen())
        app.pop_screen()
        app.push_screen(SuiteSelectionScreen())
        app.pop_screen()
        app.push_screen(RunSettingsScreen())
        app.pop_screen()
        app.push_screen(RunProgressScreen())
        app.pop_screen()
        app.push_screen(ResultsBrowserScreen())
        app.pop_screen()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local Model Benchmark TUI")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Validate imports, registries, and screen initialization.",
    )
    args = parser.parse_args(argv)

    if args.smoke_test:
        import asyncio

        asyncio.run(run_smoke_test())
        print("TUI smoke test passed")
        return 0

    BenchmarkTuiApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

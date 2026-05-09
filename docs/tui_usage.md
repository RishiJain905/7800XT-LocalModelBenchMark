# Terminal UI (TUI) Usage

## Overview

The TUI is a keyboard-driven terminal interface for selecting model configs,
choosing benchmark suites, running benchmarks, and browsing results. It is
built with [Textual](https://textual.textualize.io/).

Launch:

```powershell
python bench_tui.py
```

Smoke test (validates the TUI can start without a running server):

```powershell
python bench_tui.py --smoke-test
```

---

## Screens

### Dashboard

The Dashboard is the home screen showing the current state and available actions.

**Displayed status:**
- Selected model config ID (or "none")
- Server health status (unknown / reachable / unreachable)
- Number of selected suites
- Run settings (repeats, max tasks)
- Last run folder path
- Registry errors (if any)

**Actions:**
| Key | Action |
|-----|--------|
| `m` | Open Model Selection |
| `s` | Open Suite Selection |
| `o` | Open Run Settings |
| `h` | Check server health for selected model |
| Enter | Start the run |
| `b` | Open Results Browser |
| `q` | Quit |

Buttons are also clickable with the mouse.

---

### Model Selection

Lists all model configs found in `configs/models/`.

| Key | Action |
|-----|--------|
| Up/Down arrows | Navigate the list |
| Enter | Select the highlighted model and return to Dashboard |
| Escape | Return to Dashboard without changing selection |

If no configs are found, the list shows "No model configs found". Check that
`configs/models/` contains `.yaml` files and that the model registry loads them
without errors (errors are displayed on the Dashboard).

---

### Suite Selection

Lists all benchmark suites registered in `benchmarks/suites.yaml`. Multiple
suites can be selected — they will run sequentially.

| Key | Action |
|-----|--------|
| Up/Down arrows | Move focus between checkboxes |
| Space | Toggle the focused checkbox |
| Enter | Confirm selection and return to Dashboard |
| Escape | Return to Dashboard without saving changes |

Previously selected suites are preserved when re-opening the screen.

---

### Run Settings

Configure repeat count and optional task limit.

| Field | Default | Description |
|-------|---------|-------------|
| Repeats | `1` | Number of times to run each task |
| Max tasks | blank (all) | Limit the number of tasks to run |

| Key | Action |
|-----|--------|
| Tab | Move between fields |
| Enter / Save button | Validate and save settings |
| Escape | Return to Dashboard without saving |

**Validation rules:**
- Repeats must be a positive integer (1 or greater).
- Max tasks must be blank or a positive integer.
- Invalid values show an error message; settings are not saved until valid.

---

### Health Check

Triggered from the Dashboard by pressing `h`. The TUI calls the model's
`runtime.server_url` to verify the server is reachable.

What is checked:
- The chat completions endpoint is reachable (TCP connection succeeds).
- The `/v1/models` endpoint is tried if available (not required).
- Connection refused, timeout, non-200 responses, and invalid JSON are reported.

The health status is displayed on the Dashboard:
- **reachable**: Server responded successfully.
- **unreachable**: Server did not respond or returned an error.
- **unknown**: Health check has not been run yet.

Health check does not block running — it only informs the user.

---

### Run Progress

Shows live progress while a benchmark suite is running.

**Display:**
- Suite ID
- Completed attempts / total attempts
- Latest task ID, score, and latency
- Output folder path

| Key | Action |
|-----|--------|
| `c` | Request cancellation (finishes current attempt, then stops) |
| Escape | Return to Dashboard (run continues in background) |

**Cancellation behavior:**
- Pressing `c` sets a cancellation flag.
- The current model API call completes (it is not interrupted mid-request).
- After the current attempt finishes, the run stops.
- All completed results are written to `raw.jsonl` and the manifest is marked
  `cancelled`.
- A partial summary is written from the completed attempts.

**Background runs:**
If you press Escape to return to the Dashboard while a run is active, the run
continues in the background. Re-open the Run Progress screen to monitor it.

---

### Results Browser

Browse all completed, cancelled, and failed runs.

**Table columns:**
- Model (group header)
- Run ID
- Suite
- Status
- Started

Runs are grouped by model config ID with visual headers. Within each model group,
runs are sorted by started time (most recent first).

**Detail pane** (shown for the selected run):
- Run folder path
- Task file
- Status and started time
- Server URL
- Generation settings
- Average score, pass rate, average latency
- Artifact count and artifact folder path
- Resumable flag

| Key | Action |
|-----|--------|
| Up/Down arrows | Navigate the table |
| `r` | Resume the selected incomplete run (status `running`, `cancelled`, or `failed`) |
| Escape | Return to Dashboard |

**Resume behavior:**
- Only runs with status `running`, `cancelled`, or `failed` can be resumed.
- Completed runs show "resumable: no" and pressing `r` on them does nothing.
- Resume reads the manifest to determine original config, tasks, and completed
  attempts. Only missing attempts are re-run.
- New results are appended to the existing `raw.jsonl`.

---

## Full Keyboard Reference

| Key | Screen(s) | Action |
|-----|-----------|--------|
| Up/Down arrows | Model Selection, Suite Selection, Results Browser | Move selection |
| Enter | Dashboard | Start run |
| Enter | Model Selection | Select model |
| Enter | Suite Selection | Confirm selection |
| Enter | Run Settings | Save settings |
| Escape | All (except Dashboard) | Go back |
| Space | Suite Selection | Toggle checkbox |
| `m` | Dashboard | Model Selection |
| `s` | Dashboard | Suite Selection |
| `o` | Dashboard | Run Settings |
| `h` | Dashboard | Check health |
| `b` | Dashboard | Results Browser |
| `c` | Run Progress | Cancel run |
| `r` | Results Browser | Resume run |
| `q` | Dashboard | Quit |
| Tab | Run Settings | Move between fields |

---

## llama-server Notes

- The TUI expects `llama-server` (or any OpenAI-compatible server) to be running
  **before** the TUI is launched.
- The benchmark does not start, stop, or restart the server.
- If the server is unreachable, the Health Check will report it and you can fix
  the server without restarting the TUI.
- If the server is restarted with a different model between runs, select a
  different model config on the Dashboard before running again.

---

## Troubleshooting

| Symptom | Likely cause | Solution |
|---------|--------------|----------|
| "No model configs found" | `configs/models/` is empty or missing | Create a `.yaml` config file and place it in `configs/models/`. |
| Dashboard shows registry errors | Invalid YAML, missing fields, or duplicate IDs | Check the error message. Fix the offending config file. |
| Health check shows "unreachable" | `llama-server` is not running or wrong URL | Start `llama-server` or verify `runtime.server_url` in the config. |
| TUI crashes on launch | Missing dependency | Run `pip install -r requirements.txt` to install dependencies. |
| "No runs found" in Results Browser | No benchmarks have been run yet | Run at least one benchmark first. |
| Run progress does not update | Background thread error | Check the terminal output for error messages. |

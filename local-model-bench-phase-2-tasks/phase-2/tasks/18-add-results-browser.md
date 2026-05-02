# Task 18 - Add Results Browser

## Goal

Let users inspect previous runs from inside the terminal UI.

## Required behavior

The results browser should list:

- Model ID.
- Run ID.
- Suite ID.
- Status.
- Average score.
- Pass rate.
- Average latency.
- Artifact count.

Selecting a run should show:

- Manifest details.
- Summary.
- Raw result path.
- Artifact folder path.

## Done criteria

- Completed, cancelled, and failed runs are visible.
- Runs are grouped by model.
- Results browser handles missing/corrupt manifests gracefully.
- Tests cover run-folder discovery and summary parsing.


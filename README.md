# Free Court Watcher

Free Court Watcher is a local-first Streamlit dashboard plus data pipeline for tracking same-day public pickleball court reservation availability in Arlington.

## What it does today

- captures same-day Arlington reservation results from an already-working local Chrome session
- parses and stores those results in a local SQLite database
- renders a dashboard for viewing current availability by park and court
- adds day-specific county court-use context extracted from the official park schedule PDFs
- exports a stable dataset directory so another machine can pull the latest DB / CSV / JSON
- runs a nightly refresh locally with `launchd`

## Important current constraint

This is **not yet a pure hosted scraper**.

The current capture path depends on:
- a live local macOS user session
- Chrome being open / scriptable
- AppleScript access to Chrome

That makes it good for local automation, but not yet ideal for public server deployment.

## Current architecture

```text
Chrome session -> capture HTML -> parse -> SQLite -> Streamlit dashboard -> export latest dataset
```

Main pieces:
- `scripts/chrome_session_fetch.py` — capture Arlington search results from Chrome
- `scripts/ingest_chrome_capture.py` — parse + persist a saved HTML capture
- `scripts/nightly_capture_and_report.py` — end-to-end nightly same-day refresh + human-readable summary
- `app/streamlit_app.py` — dashboard UI
- `app/schedule_context.py` — day-specific county schedule context used in the dashboard
- `scripts/export_latest_dataset.py` — stable export files for downstream pull/upload flows

## Nightly automation

Installed schedule:
- daily at **1:00 AM America/Los_Angeles**

Repo source for the LaunchAgent:
- `ops/ai.openclaw.court-watch-nightly.plist`

Machine-loaded copy:
- `~/Library/LaunchAgents/ai.openclaw.court-watch-nightly.plist`

Logs:
- `logs/nightly.stdout.log`
- `logs/nightly.stderr.log`

## Stable export path

This directory is intended to be pulled by another machine:
- `exports/latest/`

Files:
- `exports/latest/court_watch.db`
- `exports/latest/availability.csv`
- `exports/latest/availability.json`
- `exports/latest/metadata.json`
- `exports/latest/facilities.csv`
- `exports/latest/facilities.json`
- `exports/latest/parks.json`
- `exports/latest/locations.csv`
- `exports/latest/courts.csv`
- `exports/latest/court_sports.csv`
- `exports/latest/canonical_inventory.json`

## Minimal pull set for another machine

If another machine only needs the shaped data and dashboard layer, pull these:

### Data
- `exports/latest/availability.csv`
- `exports/latest/availability.json`
- `exports/latest/metadata.json`
- `exports/latest/canonical_inventory.json`
- `exports/latest/locations.csv`
- `exports/latest/courts.csv`
- `exports/latest/court_sports.csv`

### Dashboard code
- `app/streamlit_app.py`
- `app/schedule_context.py`

That is the current clean boundary between this VM’s role (capture + shape data) and a downstream machine’s role (pull + render/upload).

Refresh it manually with:

```bash
cd /Users/varysoc/.openclaw/workspace/court-watch
./.venv/bin/python scripts/export_latest_dataset.py
```

## Local setup

```bash
cd /Users/varysoc/.openclaw/workspace/court-watch
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Useful commands

Run the dashboard:

```bash
cd /Users/varysoc/.openclaw/workspace/court-watch
./.venv/bin/python -m streamlit run app/streamlit_app.py
```

Refresh same-day data end-to-end:

```bash
cd /Users/varysoc/.openclaw/workspace/court-watch
./.venv/bin/python scripts/nightly_capture_and_report.py
```

Export stable latest dataset files:

```bash
cd /Users/varysoc/.openclaw/workspace/court-watch
./.venv/bin/python scripts/export_latest_dataset.py
```

## Project layout

```text
court-watch/
├── app/
│   ├── streamlit_app.py
│   └── schedule_context.py
├── backend/
├── data/
├── docs/
├── exports/
├── logs/
├── ops/
├── reference/
├── scripts/
└── tests/
```

## Read these first when coming back later

- `docs/PROJECT_HANDOFF.md`
- `docs/CHROME_SESSION_FETCH.md`
- `docs/DASHBOARD_RUNBOOK.md`
- `app/streamlit_app.py`
- `scripts/nightly_capture_and_report.py`
- `scripts/export_latest_dataset.py`

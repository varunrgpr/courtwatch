# Free Court Watcher — Project Handoff

This file is the fastest way to re-orient to the project later.

## What this project is

Free Court Watcher is a local-first Arlington pickleball availability tracker.

It currently does four jobs:
1. **Capture** same-day reservation search results from an already-authenticated Chrome session
2. **Parse + persist** those results into a local SQLite database
3. **Render** a Streamlit dashboard for human viewing
4. **Export** a stable dataset directory for another machine to pull and publish elsewhere

## Important current constraint

The capture flow is **not a pure server-side scraper yet**.
It currently depends on:
- a live local macOS user session
- Google Chrome being open / scriptable
- AppleScript access to Chrome

That is why automation is currently done with **launchd on this Mac/VM**, not on a public server.

## Current runtime flow

### Nightly refresh

The main automation entrypoint is:
- `scripts/nightly_capture_and_report.py`

It does:
1. call `scripts/chrome_session_fetch.py`
2. save raw HTML into `data/raw/`
3. parse the HTML into cards/slots
4. persist those rows into `court_watch.db`
5. print a verbose human-readable summary

### Dashboard

The Streamlit dashboard is:
- `app/streamlit_app.py`

It reads from:
- `backend/services/reporting.py`
- `court_watch.db`

The dashboard also includes day-specific county court-use context from:
- `app/schedule_context.py`

### Exports for downstream publishing

Stable export script:
- `scripts/export_latest_dataset.py`

Stable export directory:
- `exports/latest/`

Stable exported files:
- `exports/latest/court_watch.db`
- `exports/latest/availability.csv`
- `exports/latest/availability.json`
- `exports/latest/metadata.json`

This is the path intended for another machine to pull from.

## Automation currently installed

Installed LaunchAgent source file in repo:
- `ops/ai.openclaw.court-watch-nightly.plist`

Loaded copy on machine:
- `~/Library/LaunchAgents/ai.openclaw.court-watch-nightly.plist`

Schedule:
- **1:00 AM America/Los_Angeles daily**

Logs:
- `logs/nightly.stdout.log`
- `logs/nightly.stderr.log`

## Important local paths

Project root:
- `/Users/varysoc/.openclaw/workspace/court-watch`

Main database:
- `/Users/varysoc/.openclaw/workspace/court-watch/court_watch.db`

Raw captured HTML:
- `/Users/varysoc/.openclaw/workspace/court-watch/data/raw/`

Export directory for pull-based transfer:
- `/Users/varysoc/.openclaw/workspace/court-watch/exports/latest/`

Reference PDFs pulled from Arlington:
- `/Users/varysoc/.openclaw/workspace/court-watch/reference/pdfs/`

Rendered PDF thumbnails used during review:
- `/Users/varysoc/.openclaw/workspace/court-watch/reference/pdf-thumbs/`

## Files worth knowing first

If returning later, read these first:
1. `README.md`
2. `docs/PROJECT_HANDOFF.md`
3. `docs/CHROME_SESSION_FETCH.md`
4. `docs/DASHBOARD_RUNBOOK.md`
5. `app/streamlit_app.py`
6. `scripts/nightly_capture_and_report.py`
7. `scripts/export_latest_dataset.py`

## Suggested next improvements

1. Add export step into the nightly automation so `exports/latest/` is refreshed automatically after each capture.
2. Expand tracked parks if the reservation flow supports them cleanly.
3. Tighten / verify `app/schedule_context.py` against the county PDFs whenever those schedules change.
4. If public hosting is needed later, replace the Chrome/AppleScript dependency with a reliable server-side fetch path.

# Dashboard Runbook

## 1. Capture HTML from trusted Chrome session

```bash
cd court-watch
source .venv/bin/activate
PYTHONPATH=. python scripts/chrome_session_fetch.py --date 2026-04-26
```

## 2. Ingest the saved HTML into SQLite

```bash
source .venv/bin/activate
PYTHONPATH=. python scripts/ingest_chrome_capture.py data/raw/chrome_session_results_2026-04-26.html
```

## 3. Start Streamlit

```bash
source .venv/bin/activate
streamlit run app/streamlit_app.py
```

## Current product loop

```text
Chrome trusted session -> capture results HTML -> ingest into SQLite -> view Streamlit dashboard
```

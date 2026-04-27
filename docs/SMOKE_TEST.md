# Smoke Test

Purpose: determine whether a plain `requests.Session()` can retrieve Arlington myVSCloud results HTML successfully.

## Command

```bash
cd court-watch
source .venv/bin/activate
PYTHONPATH=. python scripts/smoke_test_fetch.py
```

## What it does

1. bootstraps a session against `search.html`
2. saves bootstrap HTML to `data/raw/bootstrap_search_page.html`
3. extracts `_csrf_token` if present
4. requests one real results page for configured locations/date
5. saves results HTML to `data/raw/search_results_YYYY-MM-DD.html`
6. runs the full-page parser against the returned HTML
7. prints a small summary

## Success signals

- results HTML contains `div.result-content`
- parser returns cards and slots
- no Cloudflare or block page is saved instead

## Failure signals

- HTTP error
- block/challenge page returned
- parser finds zero result cards
- token/cookie handling appears insufficient

## If it fails

Likely next step is Playwright-assisted bootstrap or full-browser retrieval while reusing the same parser.

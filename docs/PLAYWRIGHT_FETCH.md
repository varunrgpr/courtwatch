# Playwright Fetch Path

Use this when plain `requests.Session()` is blocked by Cloudflare or other anti-bot protections.

## Goal

Load the Arlington myVSCloud results page in a real browser context, save the returned HTML, and run the existing parser against it.

## Script

```bash
cd court-watch
source .venv/bin/activate
PYTHONPATH=. python scripts/playwright_fetch_results.py
```

## Expected setup

Python package:
- `playwright`

Browser install:
```bash
python -m playwright install chromium
```

## What the script does

1. builds the search URL with target date and locations
2. launches Chromium headlessly
3. loads the results page
4. saves HTML snapshots
5. saves a screenshot
6. runs `parse_search_results_page()` on the captured HTML
7. prints a summary

## Output files

Saved under `data/raw/`:
- `playwright_bootstrap.html`
- `playwright_results_YYYY-MM-DD.html`
- `playwright_results_YYYY-MM-DD.png`

## Success signals

- page title looks normal, not a challenge page
- HTML contains `div.result-content`
- parser returns cards and slots

## Failure signals

- challenge page or access denied page
- parser finds zero cards
- browser cannot load because Playwright/browser binaries are missing

## Important note

This is a retrieval fallback only. The parser layer remains unchanged.

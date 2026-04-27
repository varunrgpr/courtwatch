# Chrome Session Fetch

This is the current best retrieval path.

It reuses the user's already-working Chrome session instead of scraping the site like a fresh bot client.

## What it does

1. reads the active Chrome tab URL
2. swaps the `date` parameter to the target date
3. opens a new Chrome tab with that next-day search URL
4. waits for the rendered results page
5. captures `document.documentElement.outerHTML`
6. saves the HTML under `data/raw/`
7. runs the existing parser and prints a summary

## Requirements

Chrome must allow JavaScript from Apple Events:
- **View → Developer → Allow JavaScript from Apple Events**

The active Chrome tab should already be a working Arlington myVSCloud results page when you start.

## Command

```bash
cd court-watch
source .venv/bin/activate
PYTHONPATH=. python scripts/chrome_session_fetch.py
```

## Output

Saved HTML:
- `data/raw/chrome_session_results_YYYY-MM-DD.html`

Printed summary:
- requested URL
- result card count
- parsed card count
- parsed slot count
- open/unavailable counts

## Why this exists

- plain `requests` is blocked
- headless Playwright is blocked
- the user's real browser session works

So the current robust-enough strategy is:

```text
trusted Chrome session -> open target date tab -> capture HTML -> parse
```

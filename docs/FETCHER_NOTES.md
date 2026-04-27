# Fetcher Notes

This document tracks the retrieval-side plan for Arlington's myVSCloud / WebTrac results pages.

## Current retrieval strategy

Preferred first attempt:
- use a normal `requests.Session()`
- bootstrap the session by loading `search.html`
- capture cookies
- extract `_csrf_token` if present
- request the search results page with URL/form parameters
- parse returned HTML with the page parser

## Confirmed search params

Observed from browser URL and page state:
- `type=PICKLE`
- repeated `location=<CODE>` params, e.g. `FSCOT`, `HAYES`, `MARCY`, `WRC`
- `date=MM/DD/YYYY`
- `begintime=08:00 am`
- `frheadcount=2`
- `blockstodisplay=8`
- `display=Detail`
- `module=FR`
- `frwebsearch_buttonsearch=yes`
- `_csrf_token=<token>` often present in page URL

## Open retrieval unknowns

- whether a plain requests session can get through Cloudflare reliably from the intended runtime
- whether `_csrf_token` must be refreshed per session/request
- whether cookies alone are sufficient after bootstrap
- whether there are bot checks that require browser automation

## Suggested retrieval sequence

1. GET search page
2. save bootstrap HTML
3. inspect cookies + token presence
4. GET search results with target params
5. save returned HTML snapshot
6. run `parse_search_results_page(html)`

## Fallback path

If direct HTTP fetches are blocked or unstable:
- use Playwright to bootstrap/search
- export page HTML after results load
- still reuse the same parser layer

## Important design rule

Keep retrieval and parsing separate.

Even if Playwright becomes necessary, the parser should continue consuming plain saved HTML strings.

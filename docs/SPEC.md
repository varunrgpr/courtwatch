# Court Watch Specification

## 1. Product summary

Court Watch is a local-first Streamlit dashboard for Arlington pickleball players who want a daily report of playable, unreserved court windows at a selected set of public courts.

The product is not primarily about booking. It is about answering:
- which selected courts look open and playable today or tomorrow
- at what times
- with what freshness/confidence

## 2. Primary use case

A pickleball group wants a daily report of the specific Arlington courts they care about, so they can quickly spot unreserved windows for free drop-in play.

## 3. Constraints

- the source is protected by bot controls, so trusted browser-session capture is currently the viable retrieval path
- reservations can only be made one day prior
- same-day / next-day freshness matters more than long-term forecasting
- not every unreserved block is automatically playable for pickleball because dual-court schedule rules may apply

## 4. Goals

### Functional goals
- collect availability windows for selected courts
- capture park, court, date, start, end, and source status
- persist daily snapshots
- show a Streamlit dashboard focused on open/playable windows
- surface last-updated freshness clearly

### Non-functional goals
- simple to run locally on macOS
- resilient enough for daily use
- inspectable and debuggable
- preserve raw HTML snapshots for audit/recovery

## 5. Non-goals for v1

- automatic booking
- user accounts
- notifications/alerts
- predictive analytics
- general public directory for all courts everywhere
- production cloud hosting

## 6. Current retrieval strategy

The working path is:
- use the trusted local Chrome session
- open the desired myVSCloud results page in a new tab
- capture rendered HTML via Apple Events JavaScript
- parse the HTML into structured windows

This is intentionally separated from parsing and storage.

## 7. Data flow

```text
trusted Chrome session
  -> open target-date results tab
  -> capture rendered HTML
  -> save raw snapshot
  -> parse result cards + slot windows
  -> persist daily snapshot in SQLite
  -> Streamlit reads the latest snapshot
```

## 8. Canonical entities

### Park
Fields:
- id
- name
- source_park_code (optional)
- active

### Court
Fields:
- id
- park_id
- court_label
- source_facility_id
- active

### ScrapeRun
A single snapshot capture / parse run.

Fields:
- id
- target_date
- started_at
- finished_at
- status
- source_url
- raw_html_path
- parks_attempted
- parks_succeeded
- parks_failed
- records_found
- error_summary

### CourtWindow
A normalized 30-minute or aggregated window observed in the source results.

Fields:
- id
- court_id
- scrape_run_id
- slot_date
- start_time
- end_time
- source_status
- playable_status
- observed_at
- source_booking_url
- price_text
- capacity

## 9. Status model

### Source status
- `open`
- `unavailable`
- `unknown`

### Playable status
For v1:
- `playable` when source status is `open`
- `not_playable` when source status is `unavailable`
- `unknown` otherwise

Later we can add schedule-aware overrides.

## 10. Dashboard requirements

### Summary area
- target date
- last updated timestamp
- total playable windows
- number of playable courts

### Filters
- park
- court
- time range
- playable-only toggle

### Main table
Columns:
- park
- court
- date
- start
- end
- source status
- playable status

### Health panel
- last successful scrape time
- raw source path
- stale warning if data is old

## 11. Validation rules

Flag suspicious runs when:
- zero cards are parsed unexpectedly
- zero windows are parsed unexpectedly
- all statuses become unknown
- dates do not match the requested target date

## 12. Storage recommendation

Use SQLite for v1.

## 13. Risks

### Highest risks
- trusted browser session is currently required
- source UI or markup may change
- “open” does not always mean definitely playable without schedule context

### Mitigations
- keep parser and capture separate
- save raw HTML every run
- surface freshness clearly
- later add dual-court schedule logic

## 14. MVP exit criteria

V1 is complete when:
- a daily Chrome-session capture can be run for a target date
- parsed windows are written to SQLite
- Streamlit shows selected courts and their open/playable windows
- the dashboard clearly shows freshness and source date

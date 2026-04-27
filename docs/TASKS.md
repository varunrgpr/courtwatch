# Court Watch Task Breakdown

## Phase 1 — Source discovery
- [ ] Identify Arlington reservation system URL(s)
- [ ] Document booking flow
- [ ] Inspect network calls in devtools
- [ ] Confirm API vs HTML vs JS-rendered source
- [ ] Save one real sample response/page
- [ ] Verify park and court identifiers are present
- [ ] Choose scraper mode

## Phase 2 — Project scaffold
- [x] Create repo structure
- [x] Add starter README
- [x] Add spec doc
- [x] Add source-notes template
- [x] Add pyproject and env template
- [ ] Finalize dependency set

## Phase 3 — Persistence
- [ ] Define SQLAlchemy models
- [ ] Create SQLite engine/session setup
- [ ] Add table creation/bootstrap flow
- [ ] Implement upsert helpers for parks/courts/slots
- [ ] Implement scrape run persistence
- [ ] Implement raw snapshot persistence

## Phase 4 — One-park prototype
- [ ] Build source client
- [ ] Fetch one target day for one park
- [ ] Save raw snapshot
- [ ] Parse slots
- [ ] Validate parsed output
- [ ] Insert normalized rows

## Phase 5 — Multi-park ingestion
- [ ] Create park inventory config
- [ ] Iterate through all configured parks
- [ ] Add retry/backoff
- [ ] Add partial-failure handling
- [ ] Add duplicate protection
- [ ] Add run summary metrics

## Phase 6 — Robustness
- [ ] Add sanity checks for suspicious zero-result runs
- [ ] Add stale-data detection
- [ ] Add parser warning logging
- [ ] Add snapshot retention policy
- [ ] Add comparison vs previous run counts

## Phase 7 — Dashboard
- [ ] Add summary metrics
- [ ] Add filters
- [ ] Add main availability table
- [ ] Add park summary cards
- [ ] Add freshness/health panel

## Phase 8 — Scheduling
- [ ] Create production scrape command
- [ ] Add cron/launchd schedule
- [ ] Write ops runbook
- [ ] Test unattended daily runs

## Nice-to-have
- [ ] Changes since previous run
- [ ] CSV export
- [ ] Notifications for newly opened slots
- [ ] Park detail pages

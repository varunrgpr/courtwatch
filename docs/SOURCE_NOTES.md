# Source Notes

Use this file during source discovery.

## Reservation system
- Base URL: `https://vaarlingtonweb.myvscloud.com/` and `https://web1.myvscloud.com/wbwsc/vaarlingtonwt.wsc/`
- Vendor/platform: Vermont Systems / myVSCloud / WebTrac-style reservation flow
- Public browse without login? Likely yes for basic availability search
- Needs session/cookies? Probably yes for stable browsing; exact requirement still needs browser inspection
- JS-heavy? Unknown, but direct fetches are protected by Cloudflare on at least some endpoints

## Booking window rules
- Same-day visible? Likely yes
- Tomorrow visible? Likely yes, with booking constrained to one day prior
- Booking opens at: unknown
- Timezone: America/Los_Angeles locally; source likely America/New_York / Arlington local time and must be confirmed

## Network observations
- Official Arlington pickleball page: `https://www.arlingtonva.us/Government/Departments/Parks-Recreation/Programs/Sports/Pickleball`
- Official page confirms outdoor reservation link points to myVSCloud/WebTrac search flow
- Example reservation/search URL seen from official page:
  `https://web1.myvscloud.com/wbwsc/vaarlingtonwt.wsc/search.html?...&type=PICKLE&module=FR...`
- Alternate domain found in search results:
  `https://vaarlingtonweb.myvscloud.com/webtrac/web/search.html?...&type=PICKLE&module=FR...`
- Response format: not yet confirmed from browser devtools
- Direct web fetch to myvscloud endpoint from tooling returned Cloudflare block / cookie challenge

## Slot fields observed
- Park identifier: not yet confirmed
- Court identifier: not yet confirmed
- Court label: not yet confirmed
- Slot start: implied in query params and search UI, but response field structure unknown
- Slot end: unknown
- Availability status: unknown in raw response shape
- Reservation ID (if any): unknown

## Parsing notes
- Official Arlington page lists outdoor reservable parks and counts:
  - Fort Scott Park — 4 courts
  - Glebe Road Park — 4 courts
  - Hayes Park — 4 courts
  - Lubber Run Park — 4 courts
  - Marcey Road Park — 4 courts
  - Virginia Highlands — 2 courts
  - Walter Reed Park — 3 courts
- Separate request per park? unknown
- Separate request per day? likely yes or effectively yes via query params
- Pagination needed? unknown

## Risks / blockers
- Anti-bot/rate limit: yes, Cloudflare block encountered on myvscloud fetch
- Login wall: not confirmed
- CAPTCHA: not seen yet, but cookie/challenge protection is present
- Missing court numbers: unknown
- Other: there appear to be at least two related reservation domains; we need browser-level inspection to find the real availability request path

## Decision
- Chosen scraper mode: not decided yet
- Current best guess: API/XHR if browser inspection reveals a usable endpoint; otherwise authenticated/session-aware HTML parsing; Playwright only if necessary
- Why: headless browser automation should be the fallback, not the default, for a daily unattended job

## Immediate next actions
1. Open the Arlington reservation flow in a normal browser
2. Use devtools network tab while searching for pickleball availability
3. Capture the request that returns park/court slot data
4. Confirm whether the response includes court-level identifiers and open/booked states
5. Determine whether cookies/session tokens are mandatory for repeatable scripted access

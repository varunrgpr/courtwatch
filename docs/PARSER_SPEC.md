# Court Watch Parser Spec

This document defines the first real parser contract for Arlington's myVSCloud / WebTrac reservation results HTML.

## Source shape confirmed

The search results page is server-rendered HTML containing repeating result-card blocks.

Confirmed outer container pattern:

```html
<div class="result-content" data-caption="Pickleball Court #1A">
```

Each result card contains:
- court/facility name
- location / park
- date block
- details link
- one `cart-blocks` section containing slot elements

## Card-level fields

Extract from each `div.result-content`:

- `court_name`
  - preferred: `data-caption`
  - fallback: `h2 span`
- `park_name`
  - selector: `td[data-title="Location"]`
- `slot_date`
  - preferred: `.dateblock[data-tooltip]`
  - fallback: text from `.dateblock__month` + `.dateblock__day`
- `source_detail_url`
  - selector: `a[href*="iteminfo.html"]`
- `source_facility_id`
  - from detail URL `FMID=` or slot URL `FRFMIDList=`
- `capacity`
  - selector: `td[data-title="Capacity"]`
- `price_text`
  - selector: `td[data-title="Price (Res/Non Res)"]`

## Slot-level fields

Slots are inside:

```html
<div class="cart-blocks">
  <ul>
    <li>...</li>
  </ul>
</div>
```

### Open/bookable slot pattern

```html
<a class="button multi-select full-block success instant-overlay cart-button cart-button--state-block"
   href="...action=UpdateSelection...FRFMIDList=197037742...GlobalSalesArea_FRItemBeginTime=45000...GlobalSalesArea_FRItemEndTime=46800..."
   data-tooltip="Book Now"
   role="button">12:30 pm - 1:00 pm</a>
```

Extract:
- `status = open`
- `time_range_text` from anchor text
- `source_booking_url` from `href`
- `source_facility_id` from `FRFMIDList`
- `start_seconds` from `GlobalSalesArea_FRItemBeginTime`
- `end_seconds` from `GlobalSalesArea_FRItemEndTime`

### Unavailable slot pattern

```html
<a class="button full-block error cart-button cart-button--state-block cart-button--display-multiline"
   href="#"
   data-tooltip="Unavailable"
   role="button">
  <span> 8:00 am - 8:30 am</span>
  <span>Unavailable</span>
</a>
```

Extract:
- `status = unavailable`
- `time_range_text` from first span
- `status_text` from second span or `data-tooltip`
- no booking URL

## Normalized slot record

Each parsed slot should produce:

```json
{
  "park_name": "Fort Scott Park",
  "court_name": "Pickleball Court #1A",
  "source_facility_id": "197037742",
  "slot_date": "2026-04-26",
  "start_time": "12:30:00",
  "end_time": "13:00:00",
  "status": "open",
  "source_booking_url": "https://...",
  "price_text": "$6.00/$12.00",
  "capacity": 4
}
```

## Parsing rules

### Date parsing
Input may look like:
- `04/26/2026`
- tooltip-based month/day fragments on the page

Canonical output:
- ISO date `YYYY-MM-DD`

### Time parsing
Input may come from:
- visible text: `12:30 pm - 1:00 pm`
- query params: `45000`, `46800`

Canonical output:
- `start_time`: `HH:MM:SS`
- `end_time`: `HH:MM:SS`

Prefer numeric query params when present. Fall back to visible text.

### Status mapping
- slot anchor class includes `success` OR `data-tooltip="Book Now"` -> `open`
- slot anchor class includes `error` OR status text/tooltip `Unavailable` -> `unavailable`
- otherwise -> `unknown`

## Validation rules

Reject or flag card if:
- no court name
- no park name
- no slot date
- no slot elements found

Reject or flag slot if:
- time cannot be parsed
- end <= start
- status missing and cannot be inferred

## Notes

- Booking rules state players must choose 2 or 3 consecutive 30-minute slots. This does not affect availability parsing; each 30-minute block should still be stored individually.
- CSRF tokens may appear in booking URLs. Store raw href only if useful, but avoid depending on replaying it for the dashboard.
- Session/bootstrap work is separate from parsing. The parser should operate on saved HTML independently.

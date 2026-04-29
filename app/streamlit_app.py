import csv
import io
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import boto3
from botocore.exceptions import BotoCoreError, ClientError

import streamlit as st

from schedule_context import SCHEDULE_CONTEXT

st.set_page_config(page_title="Free Court Watcher", layout="wide")

_DEFAULT_BUCKET = "court-watch-data-arlington"
_DEFAULT_KEY = "availability.csv"
_DEFAULT_REGION = "us-west-2"
_DISPLAY_TIMEZONE = ZoneInfo("America/New_York")
_MAX_AGE_SECONDS = 300


def _get_secret(name: str, default: str | None = None) -> str | None:
    return st.secrets[name] if name in st.secrets else default


def _get_s3_config() -> tuple[str, str, str]:
    return (
        _get_secret("S3_BUCKET", _DEFAULT_BUCKET),
        _get_secret("S3_KEY", _DEFAULT_KEY),
        _get_secret("AWS_DEFAULT_REGION", _DEFAULT_REGION),
    )


@st.cache_resource
def _get_s3_client():
    _, _, region = _get_s3_config()
    return boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
    )


@st.cache_data(show_spinner=False, ttl=60)
def get_rows() -> list[dict]:
    # The dashboard refreshes frequently enough that a short cache keeps the UI
    # snappy without making the data feel stale during manual refreshes.
    bucket, key, _ = _get_s3_config()
    response = _get_s3_client().get_object(Bucket=bucket, Key=key)
    body = response["Body"].read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(body)))
    normalized: list[dict] = []
    for row in rows:
        payload = dict(row)
        try:
            payload["segments"] = int(payload.get("segments") or 1)
        except (TypeError, ValueError):
            payload["segments"] = 1
        normalized.append(payload)
    return normalized


def _format_time_12h(time_str: str) -> str:
    """Convert a time string (HH:MM or H:MM AM/PM) to 12-hour format like '2:30 PM'.

    Handles both 24-hour input from legacy CSVs and already-converted 12-hour
    input so the display layer is resilient to either source format.
    """
    if not time_str or time_str == "—":
        return time_str
    try:
        # Try 24-hour format first (legacy data)
        t = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        try:
            # Already in 12-hour format
            t = datetime.strptime(time_str, "%I:%M %p")
        except ValueError:
            return time_str
    formatted = t.strftime("%I:%M %p")
    return formatted[1:] if formatted.startswith("0") else formatted


_DEFAULT_OPEN_HOUR = 7   # 7 AM
_DEFAULT_CLOSE_HOUR = 22  # 10 PM


def _time_to_minutes(time_str: str) -> int:
    """Convert a time string to minutes from midnight for range math."""
    if not time_str or time_str == "—":
        return 0
    time_str = time_str.strip()
    try:
        t = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        try:
            t = datetime.strptime(time_str, "%I:%M %p")
        except ValueError:
            return 0
    return t.hour * 60 + t.minute


def _minutes_to_12h(minutes: int) -> str:
    """Convert minutes from midnight to a 12-hour time string."""
    h = minutes // 60
    m = minutes % 60
    t = datetime(2000, 1, 1, h, m)
    formatted = t.strftime("%I:%M %p")
    return formatted[1:] if formatted.startswith("0") else formatted


def _fill_operating_hours_gaps(court_rows, open_hour=_DEFAULT_OPEN_HOUR, close_hour=_DEFAULT_CLOSE_HOUR):
    """Create synthetic unavailable slots for any gaps within operating hours.

    This ensures the UI shows the full day (e.g. 7 AM – 10 PM) even when the
    scraped data stops partway through.
    """
    if not court_rows:
        return []
    template = court_rows[0]
    open_m = open_hour * 60
    close_m = close_hour * 60

    # Collect covered time ranges
    ranges = []
    for row in court_rows:
        start_m = _time_to_minutes(row["start"])
        end_m = _time_to_minutes(row["end"])
        if start_m < end_m:
            ranges.append((start_m, end_m))
    if not ranges:
        return []
    ranges.sort()

    # Merge overlapping / adjacent ranges
    merged_ranges = [list(ranges[0])]
    for start_m, end_m in ranges[1:]:
        if start_m <= merged_ranges[-1][1]:
            merged_ranges[-1][1] = max(merged_ranges[-1][1], end_m)
        else:
            merged_ranges.append([start_m, end_m])

    # Identify gaps
    gaps: list[tuple[int, int]] = []
    cursor = open_m
    for start_m, end_m in merged_ranges:
        if start_m > cursor:
            gaps.append((cursor, start_m))
        cursor = max(cursor, end_m)
    if cursor < close_m:
        gaps.append((cursor, close_m))

    return [
        {
            "park": template["park"],
            "court": template["court"],
            "date": template["date"],
            "start": _minutes_to_12h(gs),
            "end": _minutes_to_12h(ge),
            "source_status": "no_data",
            "playable_status": "not_playable",
            "observed_at": template.get("observed_at"),
            "segments": 1,
        }
        for gs, ge in gaps
    ]


def format_timestamp(value: str) -> str:
    if not value or value == "—":
        return "—"
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(_DISPLAY_TIMEZONE)
        formatted = local_dt.strftime("%b %d, %I:%M %p")
        # Strip leading zero from hour (e.g. "Apr 28, 01:30 PM" → "Apr 28, 1:30 PM")
        parts = formatted.split(", ", 1)
        if len(parts) == 2 and parts[1].startswith("0"):
            formatted = parts[0] + ", " + parts[1][1:]
        return formatted
    except Exception:
        return value


def group_by_park_and_court(rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["park"]][row["court"]].append(row)
    return grouped


def get_schedule_context(park: str, report_date: str) -> tuple[str | None, list[str]]:
    # Map the report's date to the park's human-authored court-use guidance so
    # the UI can explain why some windows may exist or be absent on a given day.
    context = SCHEDULE_CONTEXT.get(park)
    if not context:
        return None, []
    try:
        weekday = datetime.fromisoformat(report_date).strftime("%A")
    except Exception:
        weekday = None
    day_notes = context.get("days", {}).get(weekday, []) if weekday else []
    return context.get("summary"), day_notes


st.markdown(
    """
    <style>
      .cw-card {
        background: #ffffff;
        border: 1px solid #dbe7f5;
        border-radius: 20px;
        padding: 18px 20px;
        margin-bottom: 18px;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        transition: transform 180ms ease, box-shadow 180ms ease;
      }
      .cw-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
      }
      .cw-park {
        font-size: 1.12rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 12px;
      }
      .cw-court-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 14px;
      }
      .cw-court-card {
        border: 1px solid #e6eef8;
        border-radius: 18px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
        padding: 14px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
      }
      .cw-court-card:hover {
        transform: translateY(-1px);
        border-color: #c7ddfb;
        box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07);
      }
      .cw-court-card-head {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 10px;
      }
      .cw-court {
        color: #0f172a;
        font-weight: 700;
        line-height: 1.2;
      }
      .cw-court-meta {
        color: #64748b;
        font-size: 0.84rem;
        margin-top: 4px;
      }
      .cw-status {
        display: inline-flex;
        align-items: center;
        white-space: nowrap;
        padding: 5px 9px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        border: 1px solid #bfdbfe;
        background: #eff6ff;
        color: #1d4ed8;
      }
      .cw-status-muted {
        border-color: #cbd5e1;
        background: #f8fafc;
        color: #64748b;
      }
      .cw-chip-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      .cw-chip {
        display: inline-block;
        padding: 8px 13px;
        border-radius: 999px;
        border: 1px solid #93c5fd;
        background: #eff6ff;
        color: #1d4ed8;
        font-size: 0.92rem;
        font-weight: 600;
        transition: all 160ms ease;
        cursor: default;
        -webkit-tap-highlight-color: transparent;
      }
      .cw-chip:hover {
        border-color: #60a5fa;
        background: #dbeafe;
        transform: translateY(-1px);
        box-shadow: 0 6px 14px rgba(37, 99, 235, 0.12);
      }
      .cw-chip:active {
        transform: translateY(0px) scale(0.985);
      }
      .cw-chip-muted {
        border-color: #cbd5e1;
        background: #f8fafc;
        color: #64748b;
      }
      .cw-chip-muted:hover {
        border-color: #94a3b8;
        background: #f1f5f9;
        box-shadow: 0 4px 10px rgba(100, 116, 139, 0.08);
      }
      .cw-empty {
        color: #64748b;
        font-style: italic;
        padding: 4px 0;
      }
      .cw-subtle {
        color: #64748b;
        font-size: 0.92rem;
      }
      .cw-top-note {
        color: #475569;
        margin-bottom: 16px;
      }
      div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #dbe7f5;
        border-radius: 16px;
        padding: 10px 12px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
      }
      div[data-testid="stMetricLabel"] {
        color: #64748b;
      }
      div[data-testid="stMetricValue"] {
        line-height: 1.05;
      }
      .cw-meta-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
      }
      .cw-context {
        margin: 0 0 14px 0;
        padding: 12px 14px;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        background: #f8fafc;
      }
      .cw-context-title {
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 6px;
      }
      .cw-context-copy {
        color: #475569;
        font-size: 0.9rem;
        margin-bottom: 8px;
      }
      .cw-context ul {
        margin: 0;
        padding-left: 18px;
        color: #334155;
      }
      .cw-context li {
        margin: 0 0 4px 0;
      }
      .cw-context a {
        color: #1d4ed8;
        text-decoration: none;
      }
      .cw-meta-pill {
        padding: 6px 10px;
        border-radius: 999px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #475569;
        font-size: 0.8rem;
        line-height: 1.1;
      }
      @media (max-width: 900px) {
        .cw-card {
          padding: 16px;
          border-radius: 18px;
        }
        .cw-court-grid {
          grid-template-columns: 1fr;
        }
      }
      @media (max-width: 640px) {
        .cw-card {
          margin-bottom: 14px;
          padding: 14px;
        }
        .cw-park {
          font-size: 1.02rem;
          margin-bottom: 10px;
        }
        .cw-chip-wrap {
          gap: 7px;
        }
        .cw-chip {
          padding: 9px 12px;
          font-size: 0.88rem;
        }
        .cw-court-meta,
        .cw-meta-pill {
          font-size: 0.78rem;
        }
        .cw-court-card {
          padding: 12px;
        }
        .cw-court-card-head {
          flex-direction: column;
          align-items: flex-start;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Free Court Watcher")
st.caption("Daily playable court availability for selected Arlington courts")

try:
    rows = get_rows()
except (ClientError, BotoCoreError, KeyError) as exc:
    bucket, key, _ = _get_s3_config()
    st.error(f"Could not load dashboard data from s3://{bucket}/{key}.")
    st.caption("Check your Streamlit secrets and confirm the latest CSV has been uploaded to S3.")
    st.exception(exc)
    st.stop()

if not rows:
    st.warning("No stored snapshot yet. Upload the latest availability CSV first.")
    st.stop()

# --- Date selector (prominent, at the top) ---
available_dates = sorted({row["date"] for row in rows if row.get("date")})
if available_dates:
    selected_date = st.selectbox("Date", available_dates, index=len(available_dates) - 1)
else:
    selected_date = None

date_rows = [row for row in rows if row.get("date") == selected_date] if selected_date else rows

parks = sorted({row["park"] for row in date_rows if row.get("park")})
with st.expander("Filters", expanded=False):
    selected_parks = st.multiselect("Parks", parks, default=parks)
    show_unplayable = st.toggle("Include unavailable windows", value=True)

filtered = [row for row in date_rows if row.get("park") in selected_parks]
playable_rows = [row for row in filtered if row.get("playable_status") == "playable"]
if show_unplayable:
    visible_rows = filtered
else:
    visible_rows = playable_rows

last_updated = max((row.get("observed_at") for row in filtered if row.get("observed_at")), default="—")

st.caption(f"Last refreshed: {format_timestamp(last_updated)}")

grouped = group_by_park_and_court(visible_rows)

st.subheader("Open windows by court")
visible_parks = [park for park in selected_parks if park in grouped]
park_columns = st.columns(len(visible_parks)) if visible_parks else []

for column, park in zip(park_columns, visible_parks):
    summary, day_notes = get_schedule_context(park, selected_date or "")
    context_html = ""
    if summary or day_notes:
        note_items = ''.join(f'<li>{note}</li>' for note in day_notes)
        notes_html = f'<ul>{note_items}</ul>' if note_items else ''
        summary_html = f'<div class="cw-context-copy">{summary}</div>' if summary else ''
        context_html = f'<div class="cw-context"><div class="cw-context-title">Today’s court-use context</div>{summary_html}{notes_html}</div>'
    html_parts = [f'<div class="cw-card"><div class="cw-park">{park}</div>{context_html}<div class="cw-court-grid">']
    for court in sorted(grouped[park].keys()):
        court_rows = sorted(
            grouped[park][court],
            key=lambda row: (_time_to_minutes(row["start"]), _time_to_minutes(row["end"])),
        )

        # --- Fill gaps so the full operating-hours range is visible ---
        gap_rows = _fill_operating_hours_gaps(court_rows)
        all_court_rows = sorted(
            court_rows + gap_rows,
            key=lambda row: (_time_to_minutes(row["start"]), _time_to_minutes(row["end"])),
        )

        playable_count = sum(1 for r in court_rows if r["playable_status"] == "playable")

        # Build chips — only show unavailable rows when the toggle is on
        display_rows = all_court_rows if show_unplayable else [r for r in all_court_rows if r["playable_status"] == "playable"]
        chips: list[str] = []
        for row in display_rows:
            cls = "cw-chip" if row["playable_status"] == "playable" else "cw-chip cw-chip-muted"
            label = f'{_format_time_12h(row["start"])} – {_format_time_12h(row["end"])}'
            if row.get("segments", 1) > 1:
                label += f' · {row["segments"]} slots'
            if row["playable_status"] != "playable":
                label += " · unavailable"
            chips.append(f'<span class="{cls}">{label}</span>')

        # Only show a badge when the court has NO availability at all
        if playable_count == 0:
            status_html = '<span class="cw-status cw-status-muted">No Availability</span>'
        else:
            status_html = ""

        chip_html = ''.join(chips) if chips else '<div class="cw-empty">No time slots to display</div>'
        html_parts.append(
            f'<div class="cw-court-card">'
            f'<div class="cw-court-card-head">'
            f'<div><div class="cw-court">{court}</div></div>'
            f'{status_html}'
            f'</div>'
            f'<div class="cw-chip-wrap">{chip_html}</div>'
            f'</div>'
        )
    html_parts.append('</div></div>')
    with column:
        st.markdown(''.join(html_parts), unsafe_allow_html=True)

with st.expander("Raw merged rows"):
    st.dataframe(
        [
            {
                "park": row["park"],
                "court": row["court"],
                "date": row["date"],
                "start": _format_time_12h(row["start"]),
                "end": _format_time_12h(row["end"]),
                "source_status": row["source_status"],
                "playable_status": row["playable_status"],
                "merged_segments": row.get("segments", 1),
            }
            for row in visible_rows
        ],
        width="stretch",
        hide_index=True,
    )

import csv
import io
from collections import defaultdict
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

import streamlit as st

from schedule_context import SCHEDULE_CONTEXT

st.set_page_config(page_title="Free Court Watcher", layout="wide")

_DEFAULT_BUCKET = "court-watch-data-arlington"
_DEFAULT_KEY = "availability.csv"
_DEFAULT_REGION = "us-west-2"
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
    return [dict(row) for row in rows]


def format_timestamp(value: str) -> str:
    if not value or value == "—":
        return "—"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%b %d, %I:%M %p")
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
st.markdown(
    '<div class="cw-top-note">Merged continuous windows are shown by default so each court reads like one clean row.</div>',
    unsafe_allow_html=True,
)

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

parks = sorted({row["park"] for row in rows if row.get("park")})
with st.expander("Filters", expanded=False):
    selected_parks = st.multiselect("Parks", parks, default=parks)
    show_unplayable = st.toggle("Include unavailable windows", value=True)

filtered = [row for row in rows if row.get("park") in selected_parks]
playable_rows = [row for row in filtered if row.get("playable_status") == "playable"]
if show_unplayable:
    visible_rows = filtered
else:
    visible_rows = playable_rows

last_updated = max((row.get("observed_at") for row in filtered if row.get("observed_at")), default="—")
open_count = len(playable_rows)
playable_courts = len({(row.get("park"), row.get("court")) for row in playable_rows})
report_date = filtered[0]["date"] if filtered else "—"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Playable windows", open_count)
col2.metric("Playable courts", playable_courts)
col3.metric("Report date", report_date)
col4.metric("Last updated", format_timestamp(last_updated))

grouped = group_by_park_and_court(visible_rows)

st.subheader("Open windows by court")
for park in selected_parks:
    if park not in grouped:
        continue
    summary, day_notes = get_schedule_context(park, report_date)
    context_html = ""
    if summary or day_notes:
        note_items = ''.join(f'<li>{note}</li>' for note in day_notes)
        notes_html = f'<ul>{note_items}</ul>' if note_items else ''
        summary_html = f'<div class="cw-context-copy">{summary}</div>' if summary else ''
        context_html = f'<div class="cw-context"><div class="cw-context-title">Today’s court-use context</div>{summary_html}{notes_html}</div>'
    html_parts = [f'<div class="cw-card"><div class="cw-park">{park}</div>{context_html}<div class="cw-court-grid">']
    for court in sorted(grouped[park].keys()):
        court_rows = sorted(grouped[park][court], key=lambda row: (row["start"], row["end"]))
        chips: list[str] = []
        playable_chip_count = sum(1 for row in court_rows if row["playable_status"] == "playable")
        unavailable_chip_count = sum(1 for row in court_rows if row["playable_status"] != "playable")
        total_segments = sum(row.get("segments", 1) for row in court_rows)
        longest_minutes = 0
        for row in court_rows:
            if row["playable_status"] != "playable":
                continue
            start_dt = datetime.strptime(row["start"], "%H:%M")
            end_dt = datetime.strptime(row["end"], "%H:%M")
            longest_minutes = max(longest_minutes, int((end_dt - start_dt).total_seconds() // 60))
        availability_pct = round((playable_chip_count / len(court_rows)) * 100) if court_rows else 0
        if playable_chip_count and unavailable_chip_count:
            status_badge = '<span class="cw-status">Some availability</span>'
        elif playable_chip_count:
            status_badge = '<span class="cw-status">Playable</span>'
        else:
            status_badge = '<span class="cw-status cw-status-muted">Unavailable</span>'
        for row in court_rows:
            cls = "cw-chip" if row["playable_status"] == "playable" else "cw-chip cw-chip-muted"
            label = f'{row["start"]}–{row["end"]}'
            if row.get("segments", 1) > 1:
                label += f' · {row["segments"]} slots'
            if show_unplayable and row["playable_status"] != "playable":
                label += " · unavailable"
            tooltip = f'Status: {row["playable_status"].replace("_", " ")} | Source: {row["source_status"]} | Date: {row["date"]}'
            chips.append(f'<span class="{cls}" title="{tooltip}">{label}</span>')
        chip_html = ''.join(chips) if chips else '<div class="cw-empty">No matching windows</div>'
        meta_pills = ''.join([
            f'<span class="cw-meta-pill">{playable_chip_count} playable groups</span>',
            f'<span class="cw-meta-pill">{unavailable_chip_count} unavailable groups</span>',
            f'<span class="cw-meta-pill">{availability_pct}% available</span>',
            f'<span class="cw-meta-pill">Longest playable {longest_minutes} min</span>',
            f'<span class="cw-meta-pill">{total_segments} merged slots</span>',
            f'<span class="cw-meta-pill">{court_rows[0]["date"]}</span>',
        ])
        court_meta = f'<div class="cw-court-meta">Last updated {format_timestamp(max((row.get("observed_at") for row in court_rows if row.get("observed_at")), default="—"))}</div>'
        html_parts.append(
            f'<div class="cw-court-card"><div class="cw-court-card-head"><div><div class="cw-court">{court}</div>{court_meta}</div>{status_badge}</div><div class="cw-chip-wrap">{chip_html}</div><div class="cw-meta-strip">{meta_pills}</div></div>'
        )
    html_parts.append('</div></div>')
    st.markdown(''.join(html_parts), unsafe_allow_html=True)

with st.expander("Raw merged rows"):
    st.dataframe(
        [
            {
                "park": row["park"],
                "court": row["court"],
                "date": row["date"],
                "start": row["start"],
                "end": row["end"],
                "source_status": row["source_status"],
                "playable_status": row["playable_status"],
                "merged_segments": row.get("segments", 1),
            }
            for row in visible_rows
        ],
        width="stretch",
        hide_index=True,
    )

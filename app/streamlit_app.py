import csv
import io
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import streamlit as st

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover
    boto3 = None

    class BotoCoreError(Exception):
        pass

    class ClientError(Exception):
        pass

from schedule_context import SCHEDULE_CONTEXT

SCHEDULE_CONTEXT_ALIASES = {
    "Glebe Park": "Old Glebe Road Courts",
}

st.set_page_config(page_title="Free Court Watcher", layout="wide")

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "exports" / "latest"
_LOCAL_AVAILABILITY_CSV = EXPORT_DIR / "availability.csv"
_DEFAULT_BUCKET = "court-watch-data-arlington"
_DEFAULT_KEY = "availability.csv"
_DEFAULT_REGION = "us-west-2"
_DISPLAY_TIMEZONE = ZoneInfo("America/New_York")
_DEFAULT_OPEN_HOUR = 7
_DEFAULT_CLOSE_HOUR = 22
_TIME_BLOCKS = [
    (7 * 60, 10 * 60),
    (10 * 60, 13 * 60),
    (13 * 60, 16 * 60),
    (16 * 60, 19 * 60),
    (19 * 60, 22 * 60),
]


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
    if boto3 is None:
        raise RuntimeError("boto3 is not installed")
    _, _, region = _get_s3_config()
    return boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
    )


def _normalize_rows(rows: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for row in rows:
        payload = dict(row)
        try:
            payload["segments"] = int(payload.get("segments") or 1)
        except (TypeError, ValueError):
            payload["segments"] = 1
        normalized.append(payload)
    return normalized


def _read_local_rows() -> list[dict]:
    if not _LOCAL_AVAILABILITY_CSV.exists():
        return []
    rows = list(csv.DictReader(_LOCAL_AVAILABILITY_CSV.read_text(encoding="utf-8").splitlines()))
    return _normalize_rows(rows)


def _read_s3_rows() -> list[dict]:
    bucket, key, _ = _get_s3_config()
    response = _get_s3_client().get_object(Bucket=bucket, Key=key)
    body = response["Body"].read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(body)))
    return _normalize_rows(rows)


def _rows_freshness_key(rows: list[dict]) -> tuple[str, str]:
    if not rows:
        return ("", "")
    max_date = max((row.get("date") or "" for row in rows), default="")
    max_observed = max((row.get("observed_at") or "" for row in rows), default="")
    return (max_date, max_observed)


@st.cache_data(show_spinner=False, ttl=60)
def get_rows() -> list[dict]:
    local_rows = _read_local_rows()
    local_key = _rows_freshness_key(local_rows)

    try:
        s3_rows = _read_s3_rows()
    except Exception:
        if local_rows:
            return local_rows
        raise

    s3_key = _rows_freshness_key(s3_rows)
    if s3_key > local_key:
        return s3_rows
    return local_rows or s3_rows



def _format_time_12h(time_str: str) -> str:
    if not time_str or time_str == "—":
        return time_str
    try:
        t = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        try:
            t = datetime.strptime(time_str, "%I:%M %p")
        except ValueError:
            return time_str
    formatted = t.strftime("%I:%M %p")
    return formatted[1:] if formatted.startswith("0") else formatted


def _time_to_minutes(time_str: str) -> int:
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
    h = minutes // 60
    m = minutes % 60
    t = datetime(2000, 1, 1, h, m)
    formatted = t.strftime("%I:%M %p")
    return formatted[1:] if formatted.startswith("0") else formatted


def _fill_operating_hours_gaps(court_rows, open_hour=_DEFAULT_OPEN_HOUR, close_hour=_DEFAULT_CLOSE_HOUR):
    if not court_rows:
        return []
    template = court_rows[0]
    open_m = open_hour * 60
    close_m = close_hour * 60
    ranges = []
    for row in court_rows:
        start_m = _time_to_minutes(row["start"])
        end_m = _time_to_minutes(row["end"])
        if start_m < end_m:
            ranges.append((start_m, end_m))
    if not ranges:
        return []
    ranges.sort()
    merged_ranges = [list(ranges[0])]
    for start_m, end_m in ranges[1:]:
        if start_m <= merged_ranges[-1][1]:
            merged_ranges[-1][1] = max(merged_ranges[-1][1], end_m)
        else:
            merged_ranges.append([start_m, end_m])
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
            "source_status": "unreserved",
            "playable_status": "playable",
            "observed_at": template.get("observed_at"),
            "segments": 1,
        }
        for gs, ge in gaps
    ]


def _parse_clock_label(value: str) -> int:
    value = value.strip().upper().replace(" ", "")
    for fmt in ("%I:%M%p", "%I%p"):
        try:
            t = datetime.strptime(value, fmt)
            return t.hour * 60 + t.minute
        except ValueError:
            continue
    raise ValueError(f"Unsupported time label: {value}")


def _courts_for_scope(scope: str, court_name: str) -> bool:
    scope = scope.strip().lower()
    if scope.startswith("both courts"):
        return True
    if "courts 1-2" in scope:
        return "#1" in court_name or "#2" in court_name
    if "courts 2-3" in scope:
        return "#2" in court_name or "#3" in court_name
    match = re.search(r"court\s+(\d+)", scope)
    if match:
        token = f"#{match.group(1)}"
        return token in court_name
    return False


def get_schedule_context(park: str, report_date: str) -> tuple[str | None, list[str]]:
    context = SCHEDULE_CONTEXT.get(park)
    if not context and park in SCHEDULE_CONTEXT_ALIASES:
        context = SCHEDULE_CONTEXT.get(SCHEDULE_CONTEXT_ALIASES[park])
    if not context:
        return None, []
    try:
        weekday = datetime.fromisoformat(report_date).strftime("%A")
    except Exception:
        weekday = None
    day_notes = context.get("days", {}).get(weekday, []) if weekday else []
    return context.get("summary"), day_notes


def _schedule_open_play_windows(park: str, report_date: str, court_name: str) -> list[tuple[int, int]]:
    _, day_notes = get_schedule_context(park, report_date)
    windows: list[tuple[int, int]] = []
    for note in day_notes:
        if ":" not in note:
            continue
        scope, rest = note.split(":", 1)
        if not _courts_for_scope(scope, court_name):
            continue
        segments = [part.strip() for part in re.split(r",|\bthen\b", rest) if part.strip()]
        for segment in segments:
            if "drop-in pickleball" not in segment.lower():
                continue
            match = re.search(r"(\d{1,2}(?::\d{2})?\s*[ap]m)\s*-\s*(\d{1,2}(?::\d{2})?\s*[ap]m)", segment, re.I)
            if not match:
                continue
            windows.append((_parse_clock_label(match.group(1)), _parse_clock_label(match.group(2))))
    return windows


def _apply_schedule_open_play(rows: list[dict], park: str, report_date: str, court_name: str) -> list[dict]:
    windows = _schedule_open_play_windows(park, report_date, court_name)
    if not windows:
        return rows
    transformed: list[dict] = []
    for row in rows:
        row_start = _time_to_minutes(row["start"])
        row_end = _time_to_minutes(row["end"])
        if row_start >= row_end:
            transformed.append(row)
            continue
        pieces = [(row_start, row_end, row["playable_status"], row.get("source_status", ""))]
        for win_start, win_end in windows:
            next_pieces = []
            for seg_start, seg_end, seg_status, seg_source in pieces:
                overlap_start = max(seg_start, win_start)
                overlap_end = min(seg_end, win_end)
                if overlap_start >= overlap_end:
                    next_pieces.append((seg_start, seg_end, seg_status, seg_source))
                    continue
                if seg_start < overlap_start:
                    next_pieces.append((seg_start, overlap_start, seg_status, seg_source))
                next_pieces.append((overlap_start, overlap_end, "playable", "scheduled_open_play"))
                if overlap_end < seg_end:
                    next_pieces.append((overlap_end, seg_end, seg_status, seg_source))
            pieces = next_pieces
        for seg_start, seg_end, seg_status, seg_source in pieces:
            payload = dict(row)
            payload["start"] = _minutes_to_12h(seg_start)
            payload["end"] = _minutes_to_12h(seg_end)
            payload["playable_status"] = seg_status
            payload["source_status"] = seg_source
            payload["segments"] = 1
            transformed.append(payload)
    return transformed


def format_timestamp(value: str) -> str:
    if not value or value == "—":
        return "—"
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(_DISPLAY_TIMEZONE)
        formatted = local_dt.strftime("%b %d, %I:%M %p")
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


def _format_bucket_label(start_minutes: int, end_minutes: int) -> str:
    return f"{_minutes_to_12h(start_minutes)} – {_minutes_to_12h(end_minutes)}"


TIME_BLOCK_OPTIONS = [_format_bucket_label(start, end) for start, end in _TIME_BLOCKS]
DEFAULT_TIME_BLOCK_OPTIONS = [
    _format_bucket_label(10 * 60, 13 * 60),
    _format_bucket_label(13 * 60, 16 * 60),
    _format_bucket_label(16 * 60, 19 * 60),
]


def _build_time_buckets(rows: list[dict], blocks: list[tuple[int, int]] | None = None) -> list[dict]:
    blocks = blocks or _TIME_BLOCKS
    buckets: list[dict] = []
    all_courts_by_park: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        all_courts_by_park[row["park"]].add(row["court"])
    playable = [row for row in rows if row.get("playable_status") == "playable"]
    for start, end in blocks:
        block_minutes = end - start
        court_ranges: dict[str, dict[str, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
        for row in playable:
            row_start = _time_to_minutes(row["start"])
            row_end = _time_to_minutes(row["end"])
            overlap_start = max(start, row_start)
            overlap_end = min(end, row_end)
            if overlap_start >= overlap_end:
                continue
            court_ranges[row["park"]][row["court"]].append((overlap_start, overlap_end))
        entries = []
        for park in sorted(court_ranges.keys()):
            total_courts = len(all_courts_by_park[park])
            total_court_minutes = total_courts * block_minutes
            free_court_minutes = 0
            windows: list[str] = []
            for court in sorted(court_ranges[park].keys()):
                ranges = sorted(court_ranges[park][court])
                merged = [list(ranges[0])]
                for rs, re in ranges[1:]:
                    if rs <= merged[-1][1]:
                        merged[-1][1] = max(merged[-1][1], re)
                    else:
                        merged.append([rs, re])
                for rs, re in merged:
                    free_court_minutes += re - rs
                    windows.append(f"{court}: {_format_bucket_label(rs, re)}")
            avail_pct = round(free_court_minutes / total_court_minutes * 100) if total_court_minutes else 0
            entries.append({
                "park": park,
                "court_count": len(court_ranges[park]),
                "avail_pct": avail_pct,
                "windows": windows,
            })
        buckets.append({"label": _format_bucket_label(start, end), "entries": entries})
    return buckets


def _build_enriched_rows(rows: list[dict], report_date: str) -> list[dict]:
    grouped = group_by_park_and_court(rows)
    enriched: list[dict] = []
    for park, courts in grouped.items():
        for court, court_rows in courts.items():
            ordered = sorted(court_rows, key=lambda row: (_time_to_minutes(row["start"]), _time_to_minutes(row["end"])))
            gap_rows = _fill_operating_hours_gaps(ordered)
            adjusted = _apply_schedule_open_play(ordered + gap_rows, park, report_date, court)
            enriched.extend(adjusted)
    return enriched


def _sport_for_row(row: dict) -> str:
    court = (row.get("court") or "").lower()
    if "pickleball" in court:
        return "pickleball"
    if "tennis" in court:
        return "tennis"
    return "unknown"



st.markdown(
    """
    <style>
      .cw-card { background: #ffffff; border: 1px solid #dbe7f5; border-radius: 20px; padding: 18px 20px; margin-bottom: 18px; box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06); transition: transform 180ms ease, box-shadow 180ms ease; }
      .cw-card:hover { transform: translateY(-1px); box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08); }
      .cw-park { font-size: 1.12rem; font-weight: 700; color: #0f172a; margin-bottom: 12px; }
      .cw-court-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }
      .cw-court-card { border: 1px solid #e6eef8; border-radius: 18px; background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); padding: 14px; box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04); transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease; }
      .cw-court-card:hover { transform: translateY(-1px); border-color: #c7ddfb; box-shadow: 0 12px 26px rgba(15, 23, 42, 0.07); }
      .cw-court-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 10px; }
      .cw-court { color: #0f172a; font-weight: 700; line-height: 1.2; }
      .cw-court-meta { color: #64748b; font-size: 0.84rem; margin-top: 4px; }
      .cw-status { display: inline-flex; align-items: center; white-space: nowrap; padding: 5px 9px; border-radius: 999px; font-size: 0.78rem; font-weight: 700; border: 1px solid #86efac; background: #f0fdf4; color: #15803d; }
      .cw-status-muted { border-color: #fca5a5; background: #fef2f2; color: #b91c1c; }
      .cw-chip-wrap { display: flex; flex-wrap: wrap; gap: 8px; }
      .cw-chip { display: inline-block; padding: 8px 13px; border-radius: 999px; border: 1px solid #86efac; background: #f0fdf4; color: #15803d; font-size: 0.92rem; font-weight: 600; }
      .cw-chip-muted { border-color: #fca5a5; background: #fef2f2; color: #b91c1c; }
      .cw-empty { color: #64748b; font-style: italic; padding: 4px 0; }
      .cw-top-note { color: #475569; margin-bottom: 16px; }
      .cw-context { margin: 0 0 14px 0; padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 16px; background: #f8fafc; }
      .cw-context-title { font-weight: 700; color: #0f172a; margin-bottom: 6px; }
      .cw-context-copy { color: #475569; font-size: 0.9rem; margin-bottom: 8px; }
      .cw-context ul { margin: 0; padding-left: 18px; color: #334155; }
      .cw-meta-pill { padding: 6px 10px; border-radius: 999px; background: #f8fafc; border: 1px solid #e2e8f0; color: #475569; font-size: 0.8rem; line-height: 1.1; }
      .cw-meta-strip { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
      .cw-bucket-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
      .cw-bucket-card { border: 1px solid #dcfce7; border-radius: 18px; padding: 16px; background: linear-gradient(180deg, #ffffff 0%, #f7fee7 100%); box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04); }
      .cw-bucket-title { font-size: 1rem; font-weight: 800; color: #14532d; margin-bottom: 10px; }
      .cw-bucket-entry { padding: 10px 0; border-top: 1px solid #e5e7eb; }
      .cw-bucket-entry:first-of-type { border-top: 0; padding-top: 0; }
      .cw-bucket-park { font-weight: 700; color: #0f172a; margin-bottom: 4px; }
      .cw-bucket-meta { color: #15803d; font-size: 0.82rem; margin-bottom: 4px; }
      .cw-bucket-windows { color: #475569; font-size: 0.88rem; line-height: 1.4; }
      .cw-small { color: #64748b; font-size: 0.86rem; }
      @media (max-width: 900px) { .cw-card { padding: 16px; border-radius: 18px; } .cw-court-grid { grid-template-columns: 1fr; } }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Free Court Watcher")

try:
    rows = get_rows()
except (ClientError, BotoCoreError, KeyError, RuntimeError) as exc:
    bucket, key, _ = _get_s3_config()
    st.error(f"Could not load dashboard data from local exports or s3://{bucket}/{key}.")
    st.caption("Local exports are preferred. If those are absent, check your Streamlit secrets and S3 upload.")
    st.exception(exc)
    st.stop()

if not rows:
    st.warning("No stored snapshot yet. Export the latest availability CSV first.")
    st.stop()

available_dates = sorted({row["date"] for row in rows if row.get("date")})
selected_date = st.selectbox("Date", available_dates, index=len(available_dates) - 1) if available_dates else None
date_rows = [row for row in rows if row.get("date") == selected_date] if selected_date else rows

parks = sorted({row["park"] for row in date_rows if row.get("park")})
preferred = {"Fort Scott Park", "Hayes Park"}
default_parks = [p for p in parks if p in preferred] or parks
if "selected_parks" not in st.session_state:
    st.session_state["selected_parks"] = default_parks
selected_parks = st.multiselect("Parks", parks, key="selected_parks")
show_unplayable = st.toggle("Include not-reservable windows", value=True)
if "selected_time_blocks" not in st.session_state:
    st.session_state["selected_time_blocks"] = DEFAULT_TIME_BLOCK_OPTIONS
selected_time_blocks = st.multiselect("Time blocks", TIME_BLOCK_OPTIONS, key="selected_time_blocks")

filtered = [row for row in date_rows if row.get("park") in selected_parks]
playable_rows = [row for row in filtered if row.get("playable_status") == "playable"]
visible_rows = filtered if show_unplayable else playable_rows
last_updated = max((row.get("observed_at") for row in filtered if row.get("observed_at")), default="—")
enriched_rows = _build_enriched_rows(filtered, selected_date or "")

st.caption(f"Last refreshed: {format_timestamp(last_updated)}")

pickleball_rows = [row for row in visible_rows if _sport_for_row(row) == "pickleball"]
tennis_rows = [row for row in visible_rows if _sport_for_row(row) == "tennis"]
pickleball_enriched = [row for row in enriched_rows if _sport_for_row(row) == "pickleball"]
tennis_enriched = [row for row in enriched_rows if _sport_for_row(row) == "tennis"]

pickleball_tab, tennis_tab = st.tabs(["Pickleball", "Tennis"])


def render_sport_tab(label: str, sport_rows: list[dict], sport_enriched_rows: list[dict]) -> None:
    grouped = group_by_park_and_court(sport_rows)
    st.subheader(f"Best Times To Play — {label}")
    time_buckets = _build_time_buckets(sport_enriched_rows)
    if selected_time_blocks:
        time_buckets = [bucket for bucket in time_buckets if bucket["label"] in selected_time_blocks]
    bucket_cards: list[str] = ['<div class="cw-bucket-grid">']
    for bucket in time_buckets:
        body = '<div class="cw-empty">No free courts in this time block.</div>'
        if bucket["entries"]:
            entry_html = []
            for entry in bucket["entries"]:
                windows_html = "<br>".join(entry["windows"])
                entry_html.append(
                    f'<div class="cw-bucket-entry"><div class="cw-bucket-park">{entry["park"]} '
                    f'<span style="color:#15803d;font-weight:600;font-size:0.85rem">{entry["avail_pct"]}% free</span></div>'
                    f'<div class="cw-bucket-meta">{entry["court_count"]} court{"s" if entry["court_count"] != 1 else ""} free in this block</div>'
                    f'<div class="cw-bucket-windows">{windows_html}</div></div>'
                )
            body = "".join(entry_html)
        bucket_cards.append(f'<div class="cw-bucket-card"><div class="cw-bucket-title">{bucket["label"]}</div>{body}</div>')
    bucket_cards.append("</div>")
    st.markdown("".join(bucket_cards), unsafe_allow_html=True)

    with st.expander(f"Detailed by park and court — {label}", expanded=False):
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
                court_rows = sorted(grouped[park][court], key=lambda row: (_time_to_minutes(row["start"]), _time_to_minutes(row["end"])))
                gap_rows = _fill_operating_hours_gaps(court_rows)
                schedule_adjusted_rows = _apply_schedule_open_play(court_rows + gap_rows, park, selected_date or "", court)
                all_court_rows = sorted(schedule_adjusted_rows, key=lambda row: (_time_to_minutes(row["start"]), _time_to_minutes(row["end"])))
                playable_count = sum(1 for r in all_court_rows if r["playable_status"] == "playable")
                display_rows = all_court_rows if show_unplayable else [r for r in all_court_rows if r["playable_status"] == "playable"]
                chips: list[str] = []
                for row in display_rows:
                    cls = "cw-chip" if row["playable_status"] == "playable" else "cw-chip cw-chip-muted"
                    label2 = f'{_format_time_12h(row["start"])} – {_format_time_12h(row["end"])}'
                    if row.get("segments", 1) > 1:
                        label2 += f' · {row["segments"]} slots'
                    if row.get("source_status") in {"drop_in_open_play", "scheduled_open_play"}:
                        label2 += " · open play"
                    elif row["playable_status"] != "playable":
                        label2 += " · not reservable"
                    chips.append(f'<span class="{cls}">{label2}</span>')
                status_html = '' if playable_count else '<span class="cw-status cw-status-muted">No Availability</span>'
                chip_html = ''.join(chips) if chips else '<div class="cw-empty">No time slots to display</div>'
                html_parts.append(
                    f'<div class="cw-court-card"><div class="cw-court-card-head"><div><div class="cw-court">{court}</div></div>{status_html}</div><div class="cw-chip-wrap">{chip_html}</div></div>'
                )
            html_parts.append('</div></div>')
            with column:
                st.markdown(''.join(html_parts), unsafe_allow_html=True)


with pickleball_tab:
    render_sport_tab("Pickleball", pickleball_rows, pickleball_enriched)
with tennis_tab:
    render_sport_tab("Tennis", tennis_rows, tennis_enriched)

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

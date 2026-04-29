from __future__ import annotations

from sqlalchemy import select

from backend.db.session import SessionLocal
from backend.models import Court, Park, ReservationSlot, ScrapeRun


def _format_time_12h(t) -> str:
    """Format a time object to 12-hour format like '2:30 PM'."""
    formatted = t.strftime("%I:%M %p")
    return formatted[1:] if formatted.startswith("0") else formatted


def _normalize_row(park, court, slot_date, start_time, end_time, status, observed_at, scrape_run_id: int) -> dict:
    return {
        "park": park,
        "court": court,
        "date": str(slot_date),
        "start": _format_time_12h(start_time),
        "end": _format_time_12h(end_time),
        "source_status": status,
        "playable_status": "playable" if status == "open" else "not_playable" if status == "unavailable" else "unknown",
        "observed_at": observed_at.isoformat() if observed_at else None,
        "scrape_run_id": scrape_run_id,
    }


def merge_contiguous_windows(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    ordered = sorted(
        rows,
        key=lambda row: (
            row["park"],
            row["court"],
            row["date"],
            row["playable_status"],
            row["source_status"],
            row["start"],
        ),
    )
    merged: list[dict] = []
    current = dict(ordered[0])
    current["segments"] = 1

    for row in ordered[1:]:
        same_group = (
            row["park"] == current["park"]
            and row["court"] == current["court"]
            and row["date"] == current["date"]
            and row["playable_status"] == current["playable_status"]
            and row["source_status"] == current["source_status"]
        )
        contiguous = row["start"] == current["end"]
        if same_group and contiguous:
            current["end"] = row["end"]
            current["segments"] += 1
            if row.get("observed_at") and row["observed_at"] > current.get("observed_at", ""):
                current["observed_at"] = row["observed_at"]
        else:
            merged.append(current)
            current = dict(row)
            current["segments"] = 1

    merged.append(current)
    return merged


def load_latest_windows(merged: bool = False) -> list[dict]:
    db = SessionLocal()
    try:
        latest_run = db.scalar(select(ScrapeRun).order_by(ScrapeRun.id.desc()))
        if latest_run is None:
            return []
        stmt = (
            select(Park.name, Court.court_label, ReservationSlot.slot_date, ReservationSlot.start_time, ReservationSlot.end_time, ReservationSlot.status, ReservationSlot.observed_at)
            .join(Court, Court.id == ReservationSlot.court_id)
            .join(Park, Park.id == Court.park_id)
            .where(ReservationSlot.scrape_run_id == latest_run.id)
            .order_by(Park.name, Court.court_label, ReservationSlot.start_time)
        )
        rows = db.execute(stmt).all()
        payload = [
            _normalize_row(park, court, slot_date, start_time, end_time, status, observed_at, latest_run.id)
            for park, court, slot_date, start_time, end_time, status, observed_at in rows
        ]
        return merge_contiguous_windows(payload) if merged else payload
    finally:
        db.close()

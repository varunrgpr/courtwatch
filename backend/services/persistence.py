from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import select

from backend.db.session import SessionLocal
from backend.models import Court, Park, RawSnapshot, ReservationSlot, ScrapeRun
from backend.parsers.result_parser import ParsedCard
from backend.services.analytics import compute_daily_stats_for_run, upsert_day_status


def _playable_status(source_status: str) -> str:
    if source_status == "open":
        return "playable"
    if source_status == "unavailable":
        return "not_playable"
    return "unknown"


def _get_or_create_park(db, name: str) -> Park:
    park = db.scalar(select(Park).where(Park.name == name))
    if park is None:
        park = Park(name=name, active=1)
        db.add(park)
        db.flush()
    return park


def _get_or_create_court(db, park_id: int, court_label: str, source_facility_id: str | None) -> Court:
    stmt = select(Court).where(Court.park_id == park_id, Court.court_label == court_label)
    court = db.scalar(stmt)
    if court is None:
        court = Court(park_id=park_id, court_label=court_label, source_court_id=source_facility_id, active=1)
        db.add(court)
        db.flush()
    elif source_facility_id and court.source_court_id != source_facility_id:
        court.source_court_id = source_facility_id
        db.flush()
    return court


def persist_snapshot(
    cards: Iterable[ParsedCard],
    *,
    target_date,
    source_url: str,
    raw_html_path: str,
    status: str = "success",
) -> dict:
    db = SessionLocal()
    started_at = datetime.now(timezone.utc)
    try:
        run = ScrapeRun(
            target_date=target_date,
            started_at=started_at,
            status="running",
            parks_attempted=0,
            parks_succeeded=0,
            parks_failed=0,
            records_found=0,
            error_summary=None,
        )
        # attach extra attrs dynamically if schema has not been specialized yet
        if hasattr(run, "finished_at"):
            run.finished_at = None
        if hasattr(run, "error_summary"):
            run.error_summary = None
        db.add(run)
        db.flush()

        parks_seen: set[str] = set()
        records_found = 0
        for card in cards:
            park = _get_or_create_park(db, card.park_name)
            court = _get_or_create_court(db, park.id, card.court_name, card.source_facility_id)
            parks_seen.add(card.park_name)
            for slot in card.slots:
                db.add(
                    ReservationSlot(
                        court_id=court.id,
                        slot_date=slot.slot_date,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                        status=slot.status,
                        observed_at=datetime.now(timezone.utc),
                        scrape_run_id=run.id,
                        source_hash=f"{court.id}:{slot.slot_date}:{slot.start_time}:{slot.end_time}:{slot.status}",
                    )
                )
                records_found += 1

        raw = RawSnapshot(
            scrape_run_id=run.id,
            park_id=None,
            snapshot_type="chrome_session_html",
            file_path=raw_html_path,
        )
        db.add(raw)

        analytics_rows = compute_daily_stats_for_run(db, run.id)
        upsert_day_status(
            db,
            target_date,
            reservation_open=1,
            label="captured",
            notes="Derived from Chrome-session results capture",
            source="chrome_session_capture",
        )

        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        run.parks_attempted = len(parks_seen)
        run.parks_succeeded = len(parks_seen)
        run.parks_failed = 0
        run.records_found = records_found
        db.commit()
        return {
            "scrape_run_id": run.id,
            "parks": len(parks_seen),
            "records_found": records_found,
            "analytics_rows": analytics_rows,
            "raw_html_path": raw_html_path,
        }
    finally:
        db.close()

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import delete, select

from backend.models import CourtDailyStat, DayStatus, ReservationSlot


def _minutes_between(start_time, end_time) -> int:
    return (end_time.hour * 60 + end_time.minute) - (start_time.hour * 60 + start_time.minute)


def compute_daily_stats_for_run(db, scrape_run_id: int) -> int:
    rows = list(
        db.execute(
            select(
                ReservationSlot.court_id,
                ReservationSlot.slot_date,
                ReservationSlot.start_time,
                ReservationSlot.end_time,
                ReservationSlot.status,
            ).where(ReservationSlot.scrape_run_id == scrape_run_id)
        ).all()
    )
    if not rows:
        return 0

    db.execute(delete(CourtDailyStat).where(CourtDailyStat.scrape_run_id == scrape_run_id))
    grouped: dict[tuple[int, object], list[tuple]] = {}
    for row in rows:
        key = (row.court_id, row.slot_date)
        grouped.setdefault(key, []).append(row)

    count = 0
    for (court_id, slot_date), items in grouped.items():
        ordered = sorted(items, key=lambda item: item.start_time)
        total_windows = len(ordered)
        playable = [item for item in ordered if item.status == "open"]
        unavailable = [item for item in ordered if item.status == "unavailable"]
        availability_pct = round((len(playable) / total_windows) * 100) if total_windows else 0

        longest_minutes = 0
        current_start = None
        current_end = None
        for item in playable:
            if current_start is None:
                current_start = item.start_time
                current_end = item.end_time
                continue
            if item.start_time == current_end:
                current_end = item.end_time
            else:
                longest_minutes = max(longest_minutes, _minutes_between(current_start, current_end))
                current_start = item.start_time
                current_end = item.end_time
        if current_start is not None and current_end is not None:
            longest_minutes = max(longest_minutes, _minutes_between(current_start, current_end))

        first_playable_start = playable[0].start_time if playable else None
        last_playable_end = playable[-1].end_time if playable else None

        db.add(
            CourtDailyStat(
                court_id=court_id,
                slot_date=slot_date,
                scrape_run_id=scrape_run_id,
                total_windows=total_windows,
                playable_windows=len(playable),
                unavailable_windows=len(unavailable),
                availability_pct=availability_pct,
                longest_playable_minutes=longest_minutes,
                first_playable_start=first_playable_start,
                last_playable_end=last_playable_end,
            )
        )
        count += 1

    return count


def upsert_day_status(db, slot_date, *, reservation_open=None, label=None, notes=None, source="derived") -> None:
    day = db.scalar(select(DayStatus).where(DayStatus.slot_date == slot_date))
    if day is None:
        day = DayStatus(slot_date=slot_date)
        db.add(day)
    day.reservation_open = reservation_open
    day.label = label
    day.notes = notes
    day.source = source
    day.updated_at = datetime.now(timezone.utc)

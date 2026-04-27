from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class Park(Base):
    __tablename__ = "parks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    source_park_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1)


class Court(Base):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(primary_key=True)
    park_id: Mapped[int] = mapped_column(ForeignKey("parks.id"), index=True)
    court_label: Mapped[str] = mapped_column(String(255))
    source_court_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running")
    parks_attempted: Mapped[int] = mapped_column(Integer, default=0)
    parks_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    parks_failed: Mapped[int] = mapped_column(Integer, default=0)
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ReservationSlot(Base):
    __tablename__ = "reservation_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), index=True)
    slot_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(50), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id"), index=True)
    source_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class RawSnapshot(Base):
    __tablename__ = "raw_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id"), index=True)
    park_id: Mapped[Optional[int]] = mapped_column(ForeignKey("parks.id"), nullable=True)
    snapshot_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CourtDailyStat(Base):
    __tablename__ = "court_daily_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), index=True)
    slot_date: Mapped[date] = mapped_column(Date, index=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id"), index=True)
    total_windows: Mapped[int] = mapped_column(Integer, default=0)
    playable_windows: Mapped[int] = mapped_column(Integer, default=0)
    unavailable_windows: Mapped[int] = mapped_column(Integer, default=0)
    availability_pct: Mapped[int] = mapped_column(Integer, default=0)
    longest_playable_minutes: Mapped[int] = mapped_column(Integer, default=0)
    first_playable_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    last_playable_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DayStatus(Base):
    __tablename__ = "day_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    slot_date: Mapped[date] = mapped_column(Date, index=True, unique=True)
    reservation_open: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

from __future__ import annotations

from datetime import date


def run_daily_scrape(target_date: date | None = None) -> dict:
    return {
        "status": "stub",
        "message": "Source discovery not implemented yet. Fill docs/SOURCE_NOTES.md first.",
        "target_date": target_date.isoformat() if target_date else None,
    }

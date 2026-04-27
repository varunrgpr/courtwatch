from __future__ import annotations

"""Nightly same-day refresh entrypoint.

This script is the operational glue for the project:
1. capture the current day's reservation results from a trusted Chrome session
2. persist them into SQLite
3. print a verbose human-readable summary for logs / chat delivery

It is intentionally readable because this is the script most likely to be revisited
when automation breaks or behavior needs to change.
"""

import argparse
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
import sys

# Allow the script to be run directly from cron / launchd without needing a
# separate PYTHONPATH export.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.parsers.search_results_parser import parse_search_results_page
from backend.services.bootstrap import create_all
from backend.services.persistence import persist_snapshot
from backend.services.reporting import load_latest_windows
from scripts.chrome_session_fetch import capture_for_date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture court availability from Chrome, ingest it, and print a verbose text summary")
    parser.add_argument("--date", dest="target_date", help="Target date in YYYY-MM-DD format; defaults to today")
    return parser.parse_args()


def format_clock(value: str) -> str:
    """Convert stored 24-hour HH:MM strings into a human-friendly label."""
    return datetime.strptime(value, "%H:%M").strftime("%-I:%M %p")


def format_observed_at(value: str | None) -> str:
    if not value:
        return "unknown"
    dt = datetime.fromisoformat(value)
    return dt.strftime("%b %-d, %-I:%M %p")


def build_verbose_summary(target_date: date) -> str:
    """Build the plain-text summary used in logs and outbound notifications.

    The summary is intentionally verbose enough to be useful as a standalone
    message without needing to open the dashboard.
    """
    rows = [row for row in load_latest_windows(merged=True) if row.get("date") == target_date.isoformat()]
    if not rows:
        return f"Free Court Watcher for {target_date.strftime('%A, %b %-d')}: no rows were stored for that date."

    playable = [row for row in rows if row.get("playable_status") == "playable"]
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["park"]][row["court"]].append(row)

    latest_observed = max((row.get("observed_at") or "" for row in rows), default="")
    lines = [
        f"Free Court Watcher for {target_date.strftime('%A, %b %-d')}",
        f"Last updated: {format_observed_at(latest_observed)}",
        f"Playable windows: {len(playable)} across {sum(1 for courts in grouped.values() for court_rows in courts.values() if any(r.get('playable_status') == 'playable' for r in court_rows))} courts",
        "",
    ]

    for park in sorted(grouped):
        lines.append(f"{park}")
        for court in sorted(grouped[park]):
            court_rows = sorted(grouped[park][court], key=lambda row: (row["start"], row["end"]))
            available_rows = [row for row in court_rows if row.get("playable_status") == "playable"]
            if available_rows:
                windows = ", ".join(f"{format_clock(row['start'])}–{format_clock(row['end'])}" for row in available_rows)
                lines.append(f"- {court}: {windows}")
            else:
                lines.append(f"- {court}: no playable windows")
        lines.append("")

    return "\n".join(lines).strip()


def main() -> None:
    args = parse_args()
    # Product decision: the nightly 1 AM run should fetch the same calendar day,
    # not tomorrow, because late-night / early-morning users still care about
    # booking remaining windows for the current day.
    target = datetime.strptime(args.target_date, "%Y-%m-%d").date() if args.target_date else date.today()

    capture_summary = capture_for_date(target)
    saved_html = capture_summary.get("saved_html")
    if not saved_html:
        raise RuntimeError(f"Capture did not produce an HTML file: {capture_summary}")

    html_path = Path(saved_html)
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    cards = parse_search_results_page(html)

    # Ensure schema exists before writing new snapshot rows.
    create_all()
    persist_snapshot(cards, target_date=target, source_url=capture_summary.get("requested_url", "chrome-session"), raw_html_path=str(html_path))

    import subprocess
    subprocess.run(["aws", "s3", "cp", str(ROOT / "court_watch.db"), "s3://court-watch-data-arlington/court_watch.db"], check=True)

    print(build_verbose_summary(target))


if __name__ == "__main__":
    main()

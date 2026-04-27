from __future__ import annotations

"""Create a stable, pull-friendly export directory.

This script exists so a second machine can fetch predictable filenames without
needing to understand the rest of the repo layout.
"""

import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from backend.services.reporting import load_latest_windows

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "exports" / "latest"
DB_PATH = ROOT / "court_watch.db"


def main() -> None:
    # Keep filenames stable so pull scripts on another machine never have to
    # discover timestamped artifacts.
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        shutil.copy2(DB_PATH, EXPORT_DIR / "court_watch.db")

    rows = load_latest_windows(merged=True)

    csv_path = EXPORT_DIR / "availability.csv"
    json_path = EXPORT_DIR / "availability.json"
    meta_path = EXPORT_DIR / "metadata.json"

    fieldnames = [
        "park",
        "court",
        "date",
        "start",
        "end",
        "source_status",
        "playable_status",
        "observed_at",
        "scrape_run_id",
        "segments",
    ]

    # CSV is convenient for ad-hoc inspection / spreadsheet workflows.
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})

    # JSON preserves the row structure for downstream apps.
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    # metadata.json helps pull-side scripts validate freshness without needing
    # to open the DB or parse the larger CSV / JSON files.
    metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "files": {
            "db": str(EXPORT_DIR / "court_watch.db"),
            "csv": str(csv_path),
            "json": str(json_path),
        },
    }
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(str(EXPORT_DIR))


if __name__ == "__main__":
    main()

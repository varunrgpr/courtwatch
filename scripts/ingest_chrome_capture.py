from __future__ import annotations

import argparse
from pathlib import Path
from pprint import pprint

from backend.services.bootstrap import create_all
from backend.parsers.search_results_parser import parse_search_results_page
from backend.services.persistence import persist_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a saved Chrome-captured HTML results page into SQLite")
    parser.add_argument("html_path", help="Path to captured HTML file")
    parser.add_argument("--source-url", default="chrome-session", help="Source URL label to store with the run")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    html_path = Path(args.html_path)
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    cards = parse_search_results_page(html)
    target_date = cards[0].slot_date
    create_all()
    summary = persist_snapshot(cards, target_date=target_date, source_url=args.source_url, raw_html_path=str(html_path))
    pprint(summary)


if __name__ == "__main__":
    main()

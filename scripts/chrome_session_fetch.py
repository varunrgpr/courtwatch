from __future__ import annotations

import argparse
import subprocess
import time
from datetime import date, datetime, timedelta
from pprint import pprint
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from backend.config import settings
from backend.parsers.search_results_parser import SearchResultsParseError, parse_search_results_page

DEFAULT_LOCATIONS = ["FSCOT", "HAYES", "MARCY", "WRC"]
SEARCH_PREFIX = "https://vaarlingtonweb.myvscloud.com/webtrac/web/search.html"


def run_osascript(script: str, timeout_seconds: int = 20) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return result.stdout.strip()


def get_active_chrome_url() -> str:
    return run_osascript(
        'tell application "Google Chrome"\n'
        'if (count of windows) = 0 then error "No Chrome window open"\n'
        'return URL of active tab of front window\n'
        'end tell'
    )


def get_active_tab_html() -> str:
    return run_osascript(
        'tell application "Google Chrome"\n'
        'if (count of windows) = 0 then error "No Chrome window open"\n'
        'tell active tab of front window\n'
        'execute javascript "document.documentElement.outerHTML"\n'
        'end tell\n'
        'end tell'
    )


def open_new_tab(url: str) -> None:
    escaped = url.replace('"', '\\"')
    run_osascript(
        'tell application "Google Chrome"\n'
        'activate\n'
        'if (count of windows) = 0 then make new window\n'
        'tell front window\n'
        f'make new tab with properties {{URL:"{escaped}"}}\n'
        'set active tab index to (count of tabs)\n'
        'end tell\n'
        'end tell'
    )


def build_search_url_for_date(target_date: date, locations: list[str] | None = None, base_url: str | None = None) -> str:
    locations = locations or DEFAULT_LOCATIONS
    if base_url and base_url.startswith(SEARCH_PREFIX):
        parsed = urlparse(base_url)
        params = parse_qsl(parsed.query, keep_blank_values=True)
        filtered = [(k, v) for (k, v) in params if k not in {"date", "location"}]
        filtered.append(("date", target_date.strftime("%m/%d/%Y")))
        filtered.extend(("location", loc) for loc in locations)
        return urlunparse(parsed._replace(query=urlencode(filtered, doseq=True)))

    params = [
        ("Action", "Start"),
        ("SubAction", ""),
        ("type", "PICKLE"),
        ("primarycode", ""),
        ("date", target_date.strftime("%m/%d/%Y")),
        ("begintime", "08:00 am"),
        ("frheadcount", "2"),
        ("blockstodisplay", "8"),
        ("features1", ""),
        ("features2", ""),
        ("features3", ""),
        ("features4", ""),
        ("features5", ""),
        ("features6", ""),
        ("features7", ""),
        ("features8", ""),
        ("display", "Detail"),
        ("module", "FR"),
        ("multiselectlist_value", ""),
        ("frwebsearch_buttonsearch", "yes"),
    ]
    params.extend(("location", loc) for loc in locations)
    return f"{SEARCH_PREFIX}?{urlencode(params, doseq=True)}"


def wait_for_results(max_wait_seconds: int = 20) -> str:
    deadline = time.time() + max_wait_seconds
    last_html = ""
    while time.time() < deadline:
        html = get_active_tab_html()
        last_html = html
        lowered = html.lower()
        if 'class="result-content"' in html or 'attention required' in lowered or 'cloudflare' in lowered:
            return html
        time.sleep(1)
    return last_html


def capture_for_date(target_date: date, locations: list[str] | None = None) -> dict:
    settings.raw_data_path.mkdir(parents=True, exist_ok=True)
    current_url = get_active_chrome_url()
    url = build_search_url_for_date(target_date, locations=locations, base_url=current_url)
    open_new_tab(url)
    html = wait_for_results()

    output_path = settings.raw_data_path / f"chrome_session_results_{target_date.isoformat()}.html"
    output_path.write_text(html, encoding="utf-8")

    summary: dict = {
        "requested_url": url,
        "source_url": current_url,
        "saved_html": str(output_path),
        "result_cards_found": html.count('class="result-content"'),
        "cloudflare_detected": 'cloudflare' in html.lower() or 'attention required' in html.lower(),
    }

    try:
        cards = parse_search_results_page(html)
        slots = [slot for card in cards for slot in card.slots]
        summary.update(
            {
                "parsed_cards": len(cards),
                "parsed_slots": len(slots),
                "open_slots": sum(1 for s in slots if s.status == "open"),
                "unavailable_slots": sum(1 for s in slots if s.status == "unavailable"),
                "sample": {
                    "park": cards[0].park_name if cards else None,
                    "court": cards[0].court_name if cards else None,
                    "date": str(cards[0].slot_date) if cards else None,
                },
            }
        )
    except SearchResultsParseError as exc:
        summary["parse_error"] = str(exc)

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture myVSCloud results from the active Chrome session")
    parser.add_argument("--date", dest="target_date", help="Target date in YYYY-MM-DD format; defaults to today")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target = datetime.strptime(args.target_date, "%Y-%m-%d").date() if args.target_date else date.today()
    summary = capture_for_date(target)
    pprint(summary)


if __name__ == "__main__":
    main()

from __future__ import annotations

from datetime import date
from pathlib import Path
from pprint import pprint

from backend.clients.myvscloud_client import MyVSCloudClient, build_default_request
from backend.config import settings
from backend.parsers.search_results_parser import SearchResultsParseError, parse_search_results_page


def main() -> None:
    target_date = date(2026, 4, 26)
    locations = ["FSCOT", "HAYES", "MARCY", "WRC"]

    settings.raw_data_path.mkdir(parents=True, exist_ok=True)
    client = MyVSCloudClient()

    bootstrap_html = client.bootstrap_session()
    bootstrap_path = settings.raw_data_path / "bootstrap_search_page.html"
    bootstrap_path.write_text(bootstrap_html, encoding="utf-8")

    token = client.extract_csrf_token(bootstrap_html)
    request = build_default_request(target_date=target_date, locations=locations)
    results_html = client.fetch_search_results_html(request, csrf_token=token)

    results_path = settings.raw_data_path / f"search_results_{target_date.isoformat()}.html"
    results_path.write_text(results_html, encoding="utf-8")

    summary = {
        "bootstrap_path": str(bootstrap_path),
        "results_path": str(results_path),
        "csrf_token_found": bool(token),
        "results_length": len(results_html),
        "result_cards_found": results_html.count('class="result-content"'),
    }

    try:
        cards = parse_search_results_page(results_html)
        summary["parsed_cards"] = len(cards)
        summary["parsed_slots"] = sum(len(card.slots) for card in cards)
        summary["sample"] = {
            "park": cards[0].park_name,
            "court": cards[0].court_name,
            "slot_count": len(cards[0].slots),
        } if cards else None
    except SearchResultsParseError as exc:
        summary["parse_error"] = str(exc)
    except Exception as exc:  # pragma: no cover
        summary["unexpected_error"] = str(exc)

    pprint(summary)


if __name__ == "__main__":
    main()

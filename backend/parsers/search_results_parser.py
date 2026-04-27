from __future__ import annotations

from bs4 import BeautifulSoup

from backend.parsers.result_parser import ParsedCard, parse_result_card


class SearchResultsParseError(Exception):
    pass


def parse_search_results_page(html: str) -> list[ParsedCard]:
    soup = BeautifulSoup(html, "lxml")
    card_nodes = soup.select("div.result-content")
    if not card_nodes:
        raise SearchResultsParseError("no result-content cards found")

    parsed_cards: list[ParsedCard] = []
    errors: list[str] = []
    for idx, node in enumerate(card_nodes, start=1):
        try:
            parsed_cards.append(parse_result_card(str(node)))
        except Exception as exc:  # pragma: no cover - defensive aggregation path
            errors.append(f"card {idx}: {exc}")

    if not parsed_cards:
        raise SearchResultsParseError("all result cards failed to parse: " + "; ".join(errors))

    return parsed_cards

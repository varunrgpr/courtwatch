from pathlib import Path

from backend.parsers.search_results_parser import parse_search_results_page


def test_parse_search_results_page_fixture() -> None:
    html = Path("tests/fixtures/search_results_page.html").read_text(encoding="utf-8")
    cards = parse_search_results_page(html)

    assert len(cards) == 2
    assert cards[0].court_name == "Pickleball Court #1A"
    assert cards[1].court_name == "Pickleball Court #2A"

    all_slots = [slot for card in cards for slot in card.slots]
    assert len(all_slots) == 2
    assert {slot.status for slot in all_slots} == {"open", "unavailable"}

from pathlib import Path

from backend.parsers.result_parser import parse_result_card


def test_parse_result_card_fixture() -> None:
    fixture = Path("tests/fixtures/result_card_open_slot.html").read_text(encoding="utf-8")
    card = parse_result_card(fixture)

    assert card.court_name == "Pickleball Court #1A"
    assert card.park_name == "Fort Scott Park"
    assert str(card.slot_date) == "2026-04-26"
    assert card.source_facility_id == "197037742"
    assert len(card.slots) == 2

    open_slot = next(slot for slot in card.slots if slot.status == "open")
    assert open_slot.source_facility_id == "197037742"
    assert open_slot.start_time.isoformat() == "12:30:00"
    assert open_slot.end_time.isoformat() == "13:00:00"
    assert open_slot.source_booking_url is not None

    unavailable_slot = next(slot for slot in card.slots if slot.status == "unavailable")
    assert unavailable_slot.start_time.isoformat() == "14:30:00"
    assert unavailable_slot.end_time.isoformat() == "15:30:00"
    assert unavailable_slot.source_booking_url is None

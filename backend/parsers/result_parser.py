from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


@dataclass
class ParsedSlot:
    park_name: str
    court_name: str
    slot_date: date
    start_time: time
    end_time: time
    status: str
    source_facility_id: Optional[str] = None
    source_booking_url: Optional[str] = None
    capacity: Optional[int] = None
    price_text: Optional[str] = None


@dataclass
class ParsedCard:
    park_name: str
    court_name: str
    slot_date: date
    source_facility_id: Optional[str]
    capacity: Optional[int]
    price_text: Optional[str]
    slots: list[ParsedSlot]


def _text_or_none(node) -> Optional[str]:
    if node is None:
        return None
    text = node.get_text(" ", strip=True)
    return text or None


def _parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%m/%d/%Y").date()


def _parse_time_string(value: str) -> time:
    return datetime.strptime(value.strip().lower(), "%I:%M %p").time()


def _parse_time_range(value: str) -> tuple[time, time]:
    start_raw, end_raw = [part.strip() for part in value.split("-")]
    return _parse_time_string(start_raw), _parse_time_string(end_raw)


def _seconds_to_time(value: str) -> time:
    seconds = int(value)
    base = datetime(2000, 1, 1) + timedelta(seconds=seconds)
    return base.time().replace(microsecond=0)


def _extract_qs(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def _status_for_anchor(anchor) -> str:
    classes = set(anchor.get("class", []))
    tooltip = (anchor.get("data-tooltip") or anchor.get("tooltip") or "").strip().lower()
    text = anchor.get_text(" ", strip=True).lower()
    if "success" in classes or tooltip == "book now":
        return "open"
    if "error" in classes or "unavailable" in tooltip or "unavailable" in text:
        return "unavailable"
    return "unknown"


def parse_result_card(html: str) -> ParsedCard:
    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one("div.result-content")
    if root is None:
        raise ValueError("result-content root not found")

    court_name = root.get("data-caption") or _text_or_none(root.select_one("h2 span"))
    park_name = _text_or_none(root.select_one('td[data-title="Location"]'))
    date_node = root.select_one(".dateblock")
    raw_date = date_node.get("data-tooltip") if date_node is not None else None
    if not court_name or not park_name or not raw_date:
        raise ValueError("missing court_name, park_name, or raw_date")

    slot_date = _parse_date(raw_date)
    capacity_text = _text_or_none(root.select_one('td[data-title="Capacity"]'))
    price_text = _text_or_none(root.select_one('td[data-title="Price (Res/Non Res)"]'))
    detail_href = root.select_one('a[href*="iteminfo.html"]')
    detail_url = detail_href.get("href") if detail_href else None
    source_facility_id = None
    if detail_url:
        detail_qs = _extract_qs(detail_url)
        source_facility_id = (detail_qs.get("FMID") or [None])[0]

    slots: list[ParsedSlot] = []
    for anchor in root.select("div.cart-blocks li a"):
        status = _status_for_anchor(anchor)
        booking_url = anchor.get("href")
        slot_text = None
        spans = anchor.find_all("span")
        if spans:
            slot_text = _text_or_none(spans[0])
        if not slot_text:
            slot_text = _text_or_none(anchor)
        if not slot_text or "-" not in slot_text:
            continue

        start_time: time
        end_time: time
        slot_facility_id = source_facility_id
        if booking_url and booking_url != "#":
            qs = _extract_qs(booking_url)
            begin_seconds = (qs.get("GlobalSalesArea_FRItemBeginTime") or [None])[0]
            end_seconds = (qs.get("GlobalSalesArea_FRItemEndTime") or [None])[0]
            slot_facility_id = (qs.get("FRFMIDList") or [slot_facility_id])[0]
            if begin_seconds and end_seconds:
                start_time = _seconds_to_time(begin_seconds)
                end_time = _seconds_to_time(end_seconds)
            else:
                start_time, end_time = _parse_time_range(slot_text)
        else:
            start_time, end_time = _parse_time_range(slot_text)
            booking_url = None

        slots.append(
            ParsedSlot(
                park_name=park_name,
                court_name=court_name,
                slot_date=slot_date,
                start_time=start_time,
                end_time=end_time,
                status=status,
                source_facility_id=slot_facility_id,
                source_booking_url=booking_url,
                capacity=int(capacity_text) if capacity_text and capacity_text.isdigit() else None,
                price_text=price_text,
            )
        )

    if not slots:
        raise ValueError("no slots parsed from result card")

    return ParsedCard(
        park_name=park_name,
        court_name=court_name,
        slot_date=slot_date,
        source_facility_id=source_facility_id,
        capacity=int(capacity_text) if capacity_text and capacity_text.isdigit() else None,
        price_text=price_text,
        slots=slots,
    )

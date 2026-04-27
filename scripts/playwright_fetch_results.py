from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from pprint import pprint
from urllib.parse import quote

from backend.config import settings
from backend.parsers.search_results_parser import SearchResultsParseError, parse_search_results_page


def build_search_url(target_date: date, locations: list[str]) -> str:
    base = "https://vaarlingtonweb.myvscloud.com/webtrac/web/search.html"
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
    query = "&".join(f"{quote(str(k))}={quote(str(v))}" for k, v in params)
    return f"{base}?{query}"


async def fetch_results_html(target_date: date, locations: list[str]) -> dict:
    from playwright.async_api import async_playwright

    settings.raw_data_path.mkdir(parents=True, exist_ok=True)
    url = build_search_url(target_date, locations)
    bootstrap_path = settings.raw_data_path / "playwright_bootstrap.html"
    results_path = settings.raw_data_path / f"playwright_results_{target_date.isoformat()}.html"
    screenshot_path = settings.raw_data_path / f"playwright_results_{target_date.isoformat()}.png"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        bootstrap_html = await page.content()
        bootstrap_path.write_text(bootstrap_html, encoding="utf-8")

        # Wait for either results or a challenge page.
        await page.wait_for_timeout(3000)
        results_html = await page.content()
        results_path.write_text(results_html, encoding="utf-8")
        await page.screenshot(path=str(screenshot_path), full_page=True)
        final_url = page.url
        title = await page.title()

        await browser.close()

    summary = {
        "requested_url": url,
        "final_url": final_url,
        "page_title": title,
        "bootstrap_path": str(bootstrap_path),
        "results_path": str(results_path),
        "screenshot_path": str(screenshot_path),
        "result_cards_found": results_html.count('class="result-content"'),
        "cloudflare_detected": "cloudflare" in results_html.lower() or "attention required" in results_html.lower(),
    }

    try:
        cards = parse_search_results_page(results_html)
        summary["parsed_cards"] = len(cards)
        summary["parsed_slots"] = sum(len(card.slots) for card in cards)
        if cards:
            summary["sample"] = {
                "park": cards[0].park_name,
                "court": cards[0].court_name,
                "first_slot_status": cards[0].slots[0].status if cards[0].slots else None,
            }
    except SearchResultsParseError as exc:
        summary["parse_error"] = str(exc)
    except Exception as exc:  # pragma: no cover
        summary["unexpected_error"] = str(exc)

    return summary


def main() -> None:
    target_date = date(2026, 4, 26)
    locations = ["FSCOT", "HAYES", "MARCY", "WRC"]
    pprint(asyncio.run(fetch_results_html(target_date, locations)))


if __name__ == "__main__":
    main()

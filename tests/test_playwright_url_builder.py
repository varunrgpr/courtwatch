from datetime import date

from scripts.playwright_fetch_results import build_search_url


def test_build_search_url_contains_expected_params() -> None:
    url = build_search_url(date(2026, 4, 26), ["FSCOT", "WRC"])
    assert "search.html?" in url
    assert "type=PICKLE" in url
    assert "date=04/26/2026" in url or "date=04%2F26%2F2026" in url
    assert "location=FSCOT" in url
    assert "location=WRC" in url
    assert "module=FR" in url

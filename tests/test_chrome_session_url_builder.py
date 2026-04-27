from datetime import date

from scripts.chrome_session_fetch import build_search_url_for_date


def test_build_search_url_for_date_replaces_date_and_locations() -> None:
    base = (
        "https://vaarlingtonweb.myvscloud.com/webtrac/web/search.html?"
        "Action=Start&SubAction=&type=PICKLE&location=OLD1&location=OLD2&date=04%2F26%2F2026"
        "&begintime=08%3A00+am&frheadcount=2&blockstodisplay=8&display=Detail&module=FR"
    )
    url = build_search_url_for_date(date(2026, 4, 27), ["FSCOT", "WRC"], base_url=base)
    assert "date=04%2F27%2F2026" in url
    assert "location=FSCOT" in url
    assert "location=WRC" in url
    assert "location=OLD1" not in url

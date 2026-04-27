from datetime import date

from backend.clients.myvscloud_client import MyVSCloudClient, SearchRequest


def test_build_search_params_includes_locations_and_date() -> None:
    client = MyVSCloudClient()
    request = SearchRequest(target_date=date(2026, 4, 26), locations=["FSCOT", "WRC"])
    params = client.build_search_params(request, csrf_token="TOKEN")

    assert ("_csrf_token", "TOKEN") in params
    assert ("type", "PICKLE") in params
    assert ("date", "04/26/2026") in params
    assert ("location", "FSCOT") in params
    assert ("location", "WRC") in params


def test_build_search_url_contains_expected_bits() -> None:
    client = MyVSCloudClient()
    request = SearchRequest(target_date=date(2026, 4, 26), locations=["FSCOT"])
    url = client.build_search_url(request, csrf_token="TOKEN")

    assert "search.html?" in url
    assert "_csrf_token=TOKEN" in url
    assert "type=PICKLE" in url
    assert "location=FSCOT" in url
    assert "date=04%2F26%2F2026" in url

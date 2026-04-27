from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://vaarlingtonweb.myvscloud.com"
SEARCH_PATH = "/webtrac/web/search.html"


@dataclass
class SearchRequest:
    target_date: date
    locations: list[str]
    begin_time: str = "08:00 am"
    headcount: int = 2
    blocks_to_display: int = 8
    facility_type: str = "PICKLE"
    display: str = "Detail"
    module: str = "FR"


class MyVSCloudClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.last_bootstrap_html: str | None = None

    @property
    def search_url(self) -> str:
        return f"{self.base_url}{SEARCH_PATH}"

    def bootstrap_session(self) -> str:
        response = self.session.get(self.search_url, timeout=self.timeout)
        response.raise_for_status()
        self.last_bootstrap_html = response.text
        return response.text

    def extract_csrf_token(self, html: str | None = None) -> str | None:
        source = html or self.last_bootstrap_html
        if not source:
            return None
        soup = BeautifulSoup(source, "lxml")
        token_input = soup.select_one('input[name="_csrf_token"]')
        if token_input and token_input.get("value"):
            return token_input["value"]

        # Fallback: current implementation often exposes token in current URL/forms/links.
        for anchor in soup.select('a[href*="_csrf_token="]'):
            href = anchor.get("href") or ""
            if "_csrf_token=" in href:
                return href.split("_csrf_token=", 1)[1].split("&", 1)[0]
        return None

    def build_search_params(self, request: SearchRequest, csrf_token: str | None = None) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = [
            ("Action", "Start"),
            ("SubAction", ""),
            ("type", request.facility_type),
            ("primarycode", ""),
            ("date", request.target_date.strftime("%m/%d/%Y")),
            ("begintime", request.begin_time),
            ("frheadcount", str(request.headcount)),
            ("blockstodisplay", str(request.blocks_to_display)),
            ("features1", ""),
            ("features2", ""),
            ("features3", ""),
            ("features4", ""),
            ("features5", ""),
            ("features6", ""),
            ("features7", ""),
            ("features8", ""),
            ("display", request.display),
            ("module", request.module),
            ("multiselectlist_value", ""),
            ("frwebsearch_buttonsearch", "yes"),
        ]
        if csrf_token:
            params.insert(2, ("_csrf_token", csrf_token))
        for location in request.locations:
            params.append(("location", location))
        return params

    def build_search_url(self, request: SearchRequest, csrf_token: str | None = None) -> str:
        return f"{self.search_url}?{urlencode(self.build_search_params(request, csrf_token=csrf_token), doseq=True)}"

    def fetch_search_results_html(self, request: SearchRequest, csrf_token: str | None = None) -> str:
        token = csrf_token or self.extract_csrf_token()
        response = self.session.get(
            self.search_url,
            params=self.build_search_params(request, csrf_token=token),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text


def build_default_request(target_date: date, locations: Iterable[str]) -> SearchRequest:
    return SearchRequest(target_date=target_date, locations=list(locations))

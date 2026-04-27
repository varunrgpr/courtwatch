from datetime import date
from pprint import pprint

from backend.services.bootstrap import create_all
from backend.services.scrape_service import run_daily_scrape


if __name__ == "__main__":
    create_all()
    pprint(run_daily_scrape(date.today()))

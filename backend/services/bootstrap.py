from backend.db.base import Base
from backend.db.session import engine
from backend.models import Court, CourtDailyStat, DayStatus, Park, RawSnapshot, ReservationSlot, ScrapeRun  # noqa: F401


def create_all() -> None:
    Base.metadata.create_all(bind=engine)

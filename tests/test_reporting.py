from backend.services.bootstrap import create_all
from backend.services.reporting import load_latest_windows


def test_load_latest_windows_empty_db() -> None:
    create_all()
    rows = load_latest_windows()
    assert isinstance(rows, list)

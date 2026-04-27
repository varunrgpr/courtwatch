from backend.services.bootstrap import create_all


def test_bootstrap_runs() -> None:
    create_all()

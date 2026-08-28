import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.session import engine


def test_database_round_trip() -> None:
    """Real connection to the configured database (Postgres via docker compose,
    or the sqlite fallback set by tests/conftest.py when run outside Docker).
    Skips — does not fake-pass — if nothing is reachable at all."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
    except OperationalError as exc:
        pytest.skip(f"database not reachable in this environment: {exc}")
    else:
        assert result == 1

import os

# Tests must never be able to touch the developer's real local data (§86,
# §105). TEST_DATABASE_URL / TEST_REDIS_URL (set by docker-compose.yml for
# the api service) take priority over DATABASE_URL / REDIS_URL — even though
# both are already set inside Docker — specifically so a test run can never
# fall through to the real dev database just because someone forgot to wire
# a test-only override. Outside Docker, with neither set, this falls back to
# a local SQLite file, matching the pre-existing non-Docker dev loop.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "sqlite:///./test.db")
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL") or os.environ.get("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("API_SECRET_KEY", "test-only-secret-not-for-production-use")

import pathlib

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import event

import app.models  # noqa: F401 — registers ORM models on Base.metadata
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app

_API_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    """Postgres (the edupulse_test database, TEST_DATABASE_URL): runs the
    real Alembic migration chain, not just Base.metadata.create_all — some
    schema (the observations append-only trigger, migration 0004) exists
    only in the migration, not in any SQLAlchemy model construct, so
    create_all alone would silently skip it and the append-only test would
    pass for the wrong reason (§105). SQLite (local non-Docker fallback):
    still create_all, since the migration chain's Postgres-only DDL doesn't
    run there anyway."""
    if engine.dialect.name == "postgresql":
        alembic_cfg = Config(str(_API_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(_API_ROOT / "alembic"))
        command.upgrade(alembic_cfg, "head")
    else:

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_connection, _):
            dbapi_connection.execute("PRAGMA foreign_keys = ON")

        Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limit_counters():
    """The app's real Redis-backed rate limiter (§78) would otherwise let one
    test's requests count against the next test's quota, since the TestClient
    always reports the same client IP. Isolating tests from each other
    matters more here than exercising the limiter's own persistence, which
    the dedicated rate-limit test below does deliberately."""
    settings = get_settings()
    try:
        redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        for key in redis_client.scan_iter(match="ratelimit:*"):
            redis_client.delete(key)
    except RedisError:
        pass
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

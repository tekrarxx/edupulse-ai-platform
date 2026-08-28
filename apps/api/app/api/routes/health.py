import logging

from fastapi import APIRouter, Depends
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _check_database(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
        return "ok"
    except SQLAlchemyError as exc:
        logger.error("Database health check failed: %s", exc.__class__.__name__)
        return "unavailable"


def _check_redis() -> str:
    settings = get_settings()
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        return "ok"
    except RedisError as exc:
        logger.error("Redis health check failed: %s", exc.__class__.__name__)
        return "unavailable"


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Reports real, live dependency status — never a hardcoded 200 (§145)."""
    database_status = _check_database(db)
    redis_status = _check_redis()
    overall = "ok" if database_status == "ok" and redis_status == "ok" else "degraded"
    return {
        "status": overall,
        "dependencies": {
            "database": database_status,
            "redis": redis_status,
        },
    }

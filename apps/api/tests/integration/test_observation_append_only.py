import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.observation import Observation, ObservationEventType
from app.models.tenant import Tenant, TenantType


@pytest.fixture
def observation(db: Session) -> Observation:
    tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.INDIVIDUAL)
    db.add(tenant)
    db.flush()
    observation = Observation(
        tenant_id=tenant.id,
        subject_type="attempt",
        subject_id=str(uuid.uuid4()),
        event_type=ObservationEventType.TASK_COMPLETED,
        payload={},
        idempotency_key=str(uuid.uuid4()),
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def test_updating_an_observation_is_rejected_at_the_database_level(db: Session, observation: Observation) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("append-only trigger is Postgres-specific (migration 0004)")

    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("UPDATE observations SET subject_id = :new_id WHERE id = :id"), {"new_id": "x", "id": observation.id})
        db.commit()
    db.rollback()


def test_deleting_an_observation_is_rejected_at_the_database_level(db: Session, observation: Observation) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("append-only trigger is Postgres-specific (migration 0004)")

    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("DELETE FROM observations WHERE id = :id"), {"id": observation.id})
        db.commit()
    db.rollback()

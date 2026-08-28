import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.curriculum import Concept, Skill, Subject, Topic
from app.schemas.curriculum import PrerequisiteCreate
from app.services import curriculum_service


def _make_skill(db: Session, *, concept: Concept, slug: str) -> Skill:
    skill = Skill(concept_id=concept.id, slug=slug, name=slug)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@pytest.fixture
def concept(db: Session) -> Concept:
    unique = uuid.uuid4().hex[:8]
    subject = Subject(slug=f"test-subject-{unique}", name="Test Subject")
    db.add(subject)
    db.flush()
    topic = Topic(subject_id=subject.id, slug=f"test-topic-{unique}", name="Test Topic")
    db.add(topic)
    db.flush()
    concept = Concept(topic_id=topic.id, slug=f"test-concept-{unique}", name="Test Concept")
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


def test_a_skill_can_require_another(db: Session, concept: Concept) -> None:
    a = _make_skill(db, concept=concept, slug="a")
    b = _make_skill(db, concept=concept, slug="b")

    edge = curriculum_service.add_prerequisite(db, a.id, PrerequisiteCreate(prerequisite_skill_id=b.id))
    assert edge.skill_id == a.id
    assert edge.prerequisite_skill_id == b.id


def test_skill_cannot_be_its_own_prerequisite(db: Session, concept: Concept) -> None:
    a = _make_skill(db, concept=concept, slug="a")
    with pytest.raises(curriculum_service.SelfPrerequisite):
        curriculum_service.add_prerequisite(db, a.id, PrerequisiteCreate(prerequisite_skill_id=a.id))


def test_direct_two_cycle_is_rejected(db: Session, concept: Concept) -> None:
    a = _make_skill(db, concept=concept, slug="a")
    b = _make_skill(db, concept=concept, slug="b")

    curriculum_service.add_prerequisite(db, a.id, PrerequisiteCreate(prerequisite_skill_id=b.id))  # b before a
    with pytest.raises(curriculum_service.PrerequisiteCycle):
        curriculum_service.add_prerequisite(db, b.id, PrerequisiteCreate(prerequisite_skill_id=a.id))  # a before b: cycle


def test_transitive_three_cycle_is_rejected(db: Session, concept: Concept) -> None:
    a = _make_skill(db, concept=concept, slug="a")
    b = _make_skill(db, concept=concept, slug="b")
    c = _make_skill(db, concept=concept, slug="c")

    curriculum_service.add_prerequisite(db, a.id, PrerequisiteCreate(prerequisite_skill_id=b.id))  # b before a
    curriculum_service.add_prerequisite(db, b.id, PrerequisiteCreate(prerequisite_skill_id=c.id))  # c before b
    with pytest.raises(curriculum_service.PrerequisiteCycle):
        # a before c would close the loop: a needs b needs c needs a
        curriculum_service.add_prerequisite(db, c.id, PrerequisiteCreate(prerequisite_skill_id=a.id))


def test_diamond_shaped_prerequisites_are_allowed(db: Session, concept: Concept) -> None:
    """Not every shared ancestor is a cycle: a and b can both require c
    without that being circular."""
    a = _make_skill(db, concept=concept, slug="a")
    b = _make_skill(db, concept=concept, slug="b")
    c = _make_skill(db, concept=concept, slug="c")

    curriculum_service.add_prerequisite(db, a.id, PrerequisiteCreate(prerequisite_skill_id=c.id))
    curriculum_service.add_prerequisite(db, b.id, PrerequisiteCreate(prerequisite_skill_id=c.id))  # must not raise

"""Curriculum application service (§15). Not tenant-scoped — see
app/models/curriculum.py for why — so unlike auth_service there is no
tenant_id filtering here; every check is either "does this row exist" or
"would this write make the prerequisite graph invalid."
"""
from sqlalchemy.orm import Session

from app.models.curriculum import Concept, Prerequisite, Skill, SkillFacet, Subject, Topic
from app.schemas.curriculum import ConceptCreate, PrerequisiteCreate, SkillCreate, SkillFacetCreate, SubjectCreate, TopicCreate


class CurriculumError(Exception):
    pass


class SlugAlreadyExists(CurriculumError):
    pass


class ParentNotFound(CurriculumError):
    pass


class SkillNotFound(CurriculumError):
    pass


class SelfPrerequisite(CurriculumError):
    pass


class PrerequisiteCycle(CurriculumError):
    pass


def create_subject(db: Session, payload: SubjectCreate) -> Subject:
    if db.query(Subject).filter(Subject.slug == payload.slug).first() is not None:
        raise SlugAlreadyExists()
    subject = Subject(slug=payload.slug, name=payload.name)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def list_subjects(db: Session) -> list[Subject]:
    return db.query(Subject).order_by(Subject.name).all()


def create_topic(db: Session, payload: TopicCreate) -> Topic:
    if db.get(Subject, payload.subject_id) is None:
        raise ParentNotFound()
    if db.query(Topic).filter(Topic.subject_id == payload.subject_id, Topic.slug == payload.slug).first() is not None:
        raise SlugAlreadyExists()
    topic = Topic(subject_id=payload.subject_id, slug=payload.slug, name=payload.name)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


def create_concept(db: Session, payload: ConceptCreate) -> Concept:
    if db.get(Topic, payload.topic_id) is None:
        raise ParentNotFound()
    if db.query(Concept).filter(Concept.topic_id == payload.topic_id, Concept.slug == payload.slug).first() is not None:
        raise SlugAlreadyExists()
    concept = Concept(topic_id=payload.topic_id, slug=payload.slug, name=payload.name)
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


def create_skill(db: Session, payload: SkillCreate) -> Skill:
    if db.get(Concept, payload.concept_id) is None:
        raise ParentNotFound()
    if db.query(Skill).filter(Skill.concept_id == payload.concept_id, Skill.slug == payload.slug).first() is not None:
        raise SlugAlreadyExists()
    skill = Skill(
        concept_id=payload.concept_id,
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        grade_level=payload.grade_level,
        learning_outcome_code=payload.learning_outcome_code,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def get_skill(db: Session, skill_id: str) -> Skill:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise SkillNotFound()
    return skill


def add_skill_facet(db: Session, skill_id: str, payload: SkillFacetCreate) -> SkillFacet:
    if db.get(Skill, skill_id) is None:
        raise SkillNotFound()
    facet = SkillFacet(skill_id=skill_id, facet_type=payload.facet_type, description=payload.description)
    db.add(facet)
    db.commit()
    db.refresh(facet)
    return facet


def _would_create_cycle(db: Session, *, skill_id: str, prerequisite_skill_id: str) -> bool:
    """Adding the edge prerequisite_skill_id -> skill_id ("prerequisite_skill_id
    must be learned before skill_id") is only safe if skill_id cannot already
    reach prerequisite_skill_id by following existing edges forward. If it
    can, skill_id is already (transitively) required before
    prerequisite_skill_id, so also requiring prerequisite_skill_id before
    skill_id would be a contradiction — a cycle."""
    edges: dict[str, list[str]] = {}
    for row in db.query(Prerequisite.prerequisite_skill_id, Prerequisite.skill_id).all():
        edges.setdefault(row.prerequisite_skill_id, []).append(row.skill_id)

    visited: set[str] = set()
    frontier = [skill_id]
    while frontier:
        current = frontier.pop()
        if current == prerequisite_skill_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        frontier.extend(edges.get(current, []))
    return False


def add_prerequisite(db: Session, skill_id: str, payload: PrerequisiteCreate) -> Prerequisite:
    prerequisite_skill_id = payload.prerequisite_skill_id

    if db.get(Skill, skill_id) is None or db.get(Skill, prerequisite_skill_id) is None:
        raise SkillNotFound()
    if skill_id == prerequisite_skill_id:
        raise SelfPrerequisite()
    if _would_create_cycle(db, skill_id=skill_id, prerequisite_skill_id=prerequisite_skill_id):
        raise PrerequisiteCycle()

    edge = Prerequisite(skill_id=skill_id, prerequisite_skill_id=prerequisite_skill_id)
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge

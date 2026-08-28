from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import Role
from app.schemas.curriculum import (
    ConceptCreate,
    ConceptOut,
    PrerequisiteCreate,
    PrerequisiteOut,
    SkillCreate,
    SkillDetailOut,
    SkillFacetCreate,
    SkillFacetOut,
    SkillOut,
    SubjectCreate,
    SubjectOut,
    TopicCreate,
    TopicOut,
)
from app.services import curriculum_service

router = APIRouter(prefix="/curriculum")

# Read access: any authenticated user — curriculum is shared reference
# content, not tenant data (see app/models/curriculum.py). Write access:
# SUPER_ADMIN only, enforced per-route below.
_read_access = Depends(get_current_user)
_write_access = Depends(require_role(Role.SUPER_ADMIN))


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED, dependencies=[_write_access])
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)) -> SubjectOut:
    try:
        subject = curriculum_service.create_subject(db, payload)
    except curriculum_service.SlugAlreadyExists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug_already_exists")
    return SubjectOut.model_validate(subject)


@router.get("/subjects", response_model=list[SubjectOut], dependencies=[_read_access])
def list_subjects(db: Session = Depends(get_db)) -> list[SubjectOut]:
    return [SubjectOut.model_validate(s) for s in curriculum_service.list_subjects(db)]


@router.post("/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED, dependencies=[_write_access])
def create_topic(payload: TopicCreate, db: Session = Depends(get_db)) -> TopicOut:
    try:
        topic = curriculum_service.create_topic(db, payload)
    except curriculum_service.ParentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subject_not_found")
    except curriculum_service.SlugAlreadyExists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug_already_exists")
    return TopicOut.model_validate(topic)


@router.post("/concepts", response_model=ConceptOut, status_code=status.HTTP_201_CREATED, dependencies=[_write_access])
def create_concept(payload: ConceptCreate, db: Session = Depends(get_db)) -> ConceptOut:
    try:
        concept = curriculum_service.create_concept(db, payload)
    except curriculum_service.ParentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="topic_not_found")
    except curriculum_service.SlugAlreadyExists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug_already_exists")
    return ConceptOut.model_validate(concept)


@router.post("/skills", response_model=SkillOut, status_code=status.HTTP_201_CREATED, dependencies=[_write_access])
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)) -> SkillOut:
    try:
        skill = curriculum_service.create_skill(db, payload)
    except curriculum_service.ParentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="concept_not_found")
    except curriculum_service.SlugAlreadyExists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug_already_exists")
    return SkillOut.model_validate(skill)


@router.get("/skills/{skill_id}", response_model=SkillDetailOut, dependencies=[_read_access])
def get_skill(skill_id: str, db: Session = Depends(get_db)) -> SkillDetailOut:
    try:
        skill = curriculum_service.get_skill(db, skill_id)
    except curriculum_service.SkillNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill_not_found")
    return SkillDetailOut(
        **SkillOut.model_validate(skill).model_dump(),
        facets=[SkillFacetOut.model_validate(f) for f in skill.facets],
        prerequisites=[PrerequisiteOut.model_validate(p) for p in skill.prerequisites],
    )


@router.post(
    "/skills/{skill_id}/facets",
    response_model=SkillFacetOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write_access],
)
def add_skill_facet(skill_id: str, payload: SkillFacetCreate, db: Session = Depends(get_db)) -> SkillFacetOut:
    try:
        facet = curriculum_service.add_skill_facet(db, skill_id, payload)
    except curriculum_service.SkillNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill_not_found")
    return SkillFacetOut.model_validate(facet)


@router.post(
    "/skills/{skill_id}/prerequisites",
    response_model=PrerequisiteOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write_access],
)
def add_prerequisite(skill_id: str, payload: PrerequisiteCreate, db: Session = Depends(get_db)) -> PrerequisiteOut:
    try:
        edge = curriculum_service.add_prerequisite(db, skill_id, payload)
    except curriculum_service.SkillNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill_not_found")
    except curriculum_service.SelfPrerequisite:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="skill_cannot_be_its_own_prerequisite")
    except curriculum_service.PrerequisiteCycle:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prerequisite_would_create_a_cycle")
    return PrerequisiteOut.model_validate(edge)

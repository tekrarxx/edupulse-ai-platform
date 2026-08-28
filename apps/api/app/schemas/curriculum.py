from datetime import datetime

from pydantic import BaseModel, Field

from app.models.curriculum import SkillFacetType


class SubjectCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)


class SubjectOut(BaseModel):
    id: str
    slug: str
    name: str
    content_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TopicCreate(BaseModel):
    subject_id: str
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)


class TopicOut(BaseModel):
    id: str
    subject_id: str
    slug: str
    name: str
    content_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConceptCreate(BaseModel):
    topic_id: str
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)


class ConceptOut(BaseModel):
    id: str
    topic_id: str
    slug: str
    name: str
    content_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillCreate(BaseModel):
    concept_id: str
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    grade_level: int | None = Field(default=None, ge=1, le=12)
    learning_outcome_code: str | None = Field(default=None, max_length=50)


class SkillOut(BaseModel):
    id: str
    concept_id: str
    slug: str
    name: str
    description: str | None
    grade_level: int | None
    learning_outcome_code: str | None
    content_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillFacetCreate(BaseModel):
    facet_type: SkillFacetType
    description: str | None = None


class SkillFacetOut(BaseModel):
    id: str
    skill_id: str
    facet_type: SkillFacetType
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PrerequisiteCreate(BaseModel):
    prerequisite_skill_id: str


class PrerequisiteOut(BaseModel):
    id: str
    skill_id: str
    prerequisite_skill_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillDetailOut(SkillOut):
    facets: list[SkillFacetOut] = []
    prerequisites: list[PrerequisiteOut] = []

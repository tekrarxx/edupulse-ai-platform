from datetime import datetime

from pydantic import BaseModel


class ParentLinkCreate(BaseModel):
    parent_user_id: str
    student_user_id: str
    # §81: true only when the requesting staff member has already verified
    # guardian consent through an external process — this field records
    # that attestation, it does not itself collect consent.
    consent_given: bool = False


class ParentLinkOut(BaseModel):
    id: str
    tenant_id: str
    parent_user_id: str
    student_user_id: str
    consent_given_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

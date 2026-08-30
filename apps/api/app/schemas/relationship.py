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


class ParentChildOut(BaseModel):
    """A parent's own portal listing (§76-adjacent) — deliberately narrower
    than UserOut: no email, no date_of_birth. A parent needs enough to pick
    which child's dashboard to view, not their child's full account record."""

    student_user_id: str
    display_name: str
    consent_on_file: bool

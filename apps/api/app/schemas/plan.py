from pydantic import BaseModel, Field


class PlanOut(BaseModel):
    id: str
    slug: str
    name: str

    model_config = {"from_attributes": True}


class SwitchPlanRequest(BaseModel):
    plan_slug: str = Field(min_length=1, max_length=50)

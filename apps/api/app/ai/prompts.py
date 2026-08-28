"""Prompt registry (ADR-015 §1, §3). Each PromptTemplate pairs a rendering
function with the Pydantic schema the model's JSON output must validate
against — this is what makes §47 ("request structured output") concrete.

`_render_skill_explanation`'s signature deliberately accepts only already-
trusted curriculum fields (skill name/description) — never learner
free-text, attempt responses, or any PII. This is a structural enforcement
of ADR-015 §3's data-minimization scope, not just a documented convention:
there is no parameter through which anything else could reach the prompt.
"""
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, Field


class SkillExplanationOutput(BaseModel):
    """The JSON contract requested from — and validated against — the
    model. Distinct from app.schemas.ai.ExplanationResponse, which is the
    outward API response shape (this plus request/provenance metadata)."""

    explanation: str = Field(min_length=1, max_length=2000)
    key_points: list[str] = Field(min_length=1, max_length=5)


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    render: Callable[..., str]
    response_schema: type[BaseModel]


def _render_skill_explanation(*, skill_name: str, skill_description: str) -> str:
    return (
        "You are a physics tutor helping a secondary-school student in Turkey "
        "understand a curriculum skill. Given the skill name and description "
        "below (already-verified curriculum content — do not contradict it), "
        "write a short worked explanation suitable for a student who is "
        "learning this for the first time.\n\n"
        f"Skill name: {skill_name}\n"
        f"Skill description: {skill_description}\n\n"
        "Respond with ONLY a JSON object matching this exact shape, no other "
        'text: {"explanation": "<a short worked explanation, 2-4 sentences>", '
        '"key_points": ["<1 to 5 short key points>"]}'
    )


SKILL_EXPLANATION_V1 = PromptTemplate(
    name="skill_explanation",
    version="v1",
    render=_render_skill_explanation,
    response_schema=SkillExplanationOutput,
)

PROMPT_REGISTRY: dict[str, PromptTemplate] = {
    SKILL_EXPLANATION_V1.name: SKILL_EXPLANATION_V1,
}

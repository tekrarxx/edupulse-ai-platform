"""SkillExplanationOutput's tolerance for a real, live-verified small-model
failure mode (llama3.2:1b returning key_points as a bracketed string
instead of a JSON array) — found by manually exercising the AI Gateway
against a real local Ollama instance, ADR-015's own flagged open item.
"""
import pytest
from pydantic import ValidationError

from app.ai.prompts import SkillExplanationOutput


def test_accepts_a_genuine_json_array_unchanged() -> None:
    output = SkillExplanationOutput(explanation="F = m*a.", key_points=["Force", "Mass", "Acceleration"])
    assert output.key_points == ["Force", "Mass", "Acceleration"]


def test_normalizes_a_bracketed_comma_separated_string() -> None:
    """The exact shape observed live: '"key_points": "[F=ma, F=ma]"'."""
    output = SkillExplanationOutput(explanation="F = m*a.", key_points="[F=ma, F=ma, ma=F/r, ma=F/1]")
    assert output.key_points == ["F=ma", "F=ma", "ma=F/r", "ma=F/1"]


def test_strips_stray_quotes_inside_the_bracketed_string() -> None:
    output = SkillExplanationOutput(explanation="F = m*a.", key_points='["Force equals mass times acceleration", "Unit is Newton"]')
    assert output.key_points == ["Force equals mass times acceleration", "Unit is Newton"]


def test_still_rejects_a_genuinely_unparseable_string() -> None:
    """§47/§90: only the one unambiguous bracketed-list shape is tolerated
    — an arbitrary malformed string must still fail validation, not be
    silently coerced into a fabricated single-item list (§105)."""
    with pytest.raises(ValidationError):
        SkillExplanationOutput(explanation="F = m*a.", key_points="not a list at all")


def test_still_rejects_an_empty_bracketed_string() -> None:
    with pytest.raises(ValidationError):
        SkillExplanationOutput(explanation="F = m*a.", key_points="[]")

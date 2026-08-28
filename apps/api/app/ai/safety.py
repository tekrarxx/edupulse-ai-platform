"""Minimal output safety checks (ADR-015 §4). Explicitly NOT a claim of real
content-moderation coverage — non-empty, a hard length ceiling (defense in
depth beyond the response schema's own max_length), and a small literal
denylist. No confidence score, no factual-accuracy check, no bias
detection. §82: "never assume a confident LLM is a correct LLM" — passing
this check means the text isn't empty, absurdly long, or one of a handful
of denylisted strings; it says nothing about whether the content is
educationally correct.
"""

_MAX_LENGTH = 4000
_DENYLIST = (
    "ignore previous instructions",
    "you are now",
)


class SafetyViolation(Exception):
    pass


def validate_output_safety(text: str) -> None:
    if not text or not text.strip():
        raise SafetyViolation("empty_output")
    if len(text) > _MAX_LENGTH:
        raise SafetyViolation("output_too_long")
    lowered = text.lower()
    for phrase in _DENYLIST:
        if phrase in lowered:
            raise SafetyViolation("denylisted_content")

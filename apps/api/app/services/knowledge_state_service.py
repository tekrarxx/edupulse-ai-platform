"""Knowledge state application service (ADR-012).

`compute_knowledge_state` is the pure mathematical core — no DB session, no
implicit `datetime.now()` — so it is directly property-testable and its
output is a pure function of `(evidence_rows, as_of)` (§99 reproducibility).
`get_or_recompute_knowledge_state` is the only code path that writes the
`knowledge_states` table, and it always recomputes from the Evidence log
before upserting (ADR-012: "recompute from log, don't mutate incrementally").
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.curriculum import Skill, SkillFacetType
from app.models.evidence import Evidence, EvidenceDirectness, EvidencePolarity
from app.models.knowledge_state import ConfidenceLabel, KnowledgeState
from app.models.observation import Observation

MODEL_VERSION = "bayesian-beta-binomial-v1"

# ADR-012 constants. A change to any of these requires a model_version bump.
ALPHA_PRIOR = 1.0
BETA_PRIOR = 1.0
HALF_LIFE_DAYS = 60.0
_DIRECTNESS_MULTIPLIER = {
    EvidenceDirectness.DIRECT: 1.0,
    EvidenceDirectness.INDIRECT: 0.4,
}
_INSUFFICIENT_EVIDENCE_THRESHOLD = 1.0
_LOW_CONFIDENCE_THRESHOLD = 4.0


class KnowledgeStateError(Exception):
    pass


class SkillNotFound(KnowledgeStateError):
    pass


@dataclass(frozen=True)
class KnowledgeStateResult:
    """The pure computation's output — everything `get_or_recompute_knowledge_state`
    needs to persist, and everything an API response needs to render."""

    alpha: float
    beta: float
    mastery_probability: float
    confidence_label: ConfidenceLabel
    effective_n: float
    variance: float
    evidence_count: int
    model_version: str
    as_of: datetime


def _evidence_weight(evidence: Evidence, occurred_at: datetime, as_of: datetime) -> float:
    age_days = max((as_of - occurred_at).total_seconds(), 0.0) / 86400.0
    decay = 0.5 ** (age_days / HALF_LIFE_DAYS)
    directness_multiplier = _DIRECTNESS_MULTIPLIER[evidence.directness]
    return evidence.reliability * evidence.task_validity * evidence.evaluation_confidence * directness_multiplier * decay


def _confidence_label(effective_n: float) -> ConfidenceLabel:
    if effective_n < _INSUFFICIENT_EVIDENCE_THRESHOLD:
        return ConfidenceLabel.INSUFFICIENT_EVIDENCE
    if effective_n < _LOW_CONFIDENCE_THRESHOLD:
        return ConfidenceLabel.LOW_CONFIDENCE
    return ConfidenceLabel.HIGH_CONFIDENCE


def compute_knowledge_state(
    evidence_rows: list[tuple[Evidence, datetime]], *, as_of: datetime
) -> KnowledgeStateResult:
    """`evidence_rows`: (Evidence, observation.occurred_at) pairs, already
    filtered to exactly one (student, skill, facet) — see ADR-012's facet
    independence assumption. Order-independent: the update is a commutative
    sum, so any permutation of the same rows yields an identical result at
    the same `as_of` (§99)."""
    alpha = ALPHA_PRIOR
    beta = BETA_PRIOR
    for evidence, occurred_at in evidence_rows:
        weight = _evidence_weight(evidence, occurred_at, as_of)
        if evidence.polarity == EvidencePolarity.POSITIVE:
            alpha += weight
        else:
            beta += weight

    mastery_probability = alpha / (alpha + beta)
    effective_n = alpha + beta - ALPHA_PRIOR - BETA_PRIOR
    variance = (alpha * beta) / (((alpha + beta) ** 2) * (alpha + beta + 1))

    return KnowledgeStateResult(
        alpha=alpha,
        beta=beta,
        mastery_probability=mastery_probability,
        confidence_label=_confidence_label(effective_n),
        effective_n=effective_n,
        variance=variance,
        evidence_count=len(evidence_rows),
        model_version=MODEL_VERSION,
        as_of=as_of,
    )


def _apply_result_to_state(state: KnowledgeState, result: KnowledgeStateResult) -> None:
    state.alpha = result.alpha
    state.beta = result.beta
    state.mastery_probability = result.mastery_probability
    state.confidence_label = result.confidence_label
    state.effective_n = result.effective_n
    state.variance = result.variance
    state.evidence_count = result.evidence_count
    state.model_version = result.model_version
    state.as_of = result.as_of
    state.computed_at = datetime.now(timezone.utc)


def get_or_recompute_knowledge_state(
    db: Session,
    *,
    tenant_id: str,
    student_user_id: str,
    skill_id: str,
    facet_type: SkillFacetType,
    as_of: datetime | None = None,
) -> KnowledgeState:
    if db.get(Skill, skill_id) is None:
        raise SkillNotFound()

    as_of = as_of or datetime.now(timezone.utc)

    evidence_rows = (
        db.query(Evidence, Observation.occurred_at)
        .join(Observation, Evidence.observation_id == Observation.id)
        .filter(
            Evidence.tenant_id == tenant_id,
            Evidence.student_user_id == student_user_id,
            Evidence.skill_id == skill_id,
            Evidence.facet_type == facet_type,
        )
        .all()
    )
    result = compute_knowledge_state(list(evidence_rows), as_of=as_of)

    state = (
        db.query(KnowledgeState)
        .filter(
            KnowledgeState.tenant_id == tenant_id,
            KnowledgeState.student_user_id == student_user_id,
            KnowledgeState.skill_id == skill_id,
            KnowledgeState.facet_type == facet_type,
        )
        .first()
    )
    if state is None:
        state = KnowledgeState(
            tenant_id=tenant_id,
            student_user_id=student_user_id,
            skill_id=skill_id,
            facet_type=facet_type,
        )
        db.add(state)

    _apply_result_to_state(state, result)

    db.commit()
    db.refresh(state)
    return state


def get_knowledge_states_for_skill(
    db: Session,
    *,
    tenant_id: str,
    student_user_id: str,
    skill_id: str,
    as_of: datetime | None = None,
) -> list[KnowledgeState]:
    """All five facets (§28) for one (student, skill), each computed
    independently — see ADR-012 facet-independence assumption. Batched
    (LOAD-TEST.md's diagnosed bottleneck, ADR-012 Addendum): one Skill
    lookup, one Evidence+Observation query grouped by facet in Python, one
    KnowledgeState query, and one commit — instead of the previous
    per-facet loop's 5x each. `compute_knowledge_state` (the pure
    Bayesian core) and the field-by-field upsert
    (`_apply_result_to_state`) are exactly the same code either way, so
    the *values* this produces are identical to the old per-facet path,
    not merely similar — verified by
    tests/unit/test_knowledge_state_math.py's batching-reproducibility test."""
    if db.get(Skill, skill_id) is None:
        raise SkillNotFound()

    as_of = as_of or datetime.now(timezone.utc)

    all_evidence_rows = (
        db.query(Evidence, Observation.occurred_at)
        .join(Observation, Evidence.observation_id == Observation.id)
        .filter(Evidence.tenant_id == tenant_id, Evidence.student_user_id == student_user_id, Evidence.skill_id == skill_id)
        .all()
    )
    rows_by_facet: dict[SkillFacetType, list[tuple[Evidence, datetime]]] = {facet: [] for facet in SkillFacetType}
    for evidence, occurred_at in all_evidence_rows:
        rows_by_facet[evidence.facet_type].append((evidence, occurred_at))

    existing_states = {
        state.facet_type: state
        for state in db.query(KnowledgeState)
        .filter(
            KnowledgeState.tenant_id == tenant_id,
            KnowledgeState.student_user_id == student_user_id,
            KnowledgeState.skill_id == skill_id,
        )
        .all()
    }

    ordered_states: list[KnowledgeState] = []
    for facet_type in SkillFacetType:
        result = compute_knowledge_state(rows_by_facet[facet_type], as_of=as_of)
        state = existing_states.get(facet_type)
        if state is None:
            state = KnowledgeState(
                tenant_id=tenant_id, student_user_id=student_user_id, skill_id=skill_id, facet_type=facet_type
            )
            db.add(state)
        _apply_result_to_state(state, result)
        ordered_states.append(state)

    db.commit()
    for state in ordered_states:
        db.refresh(state)
    return ordered_states

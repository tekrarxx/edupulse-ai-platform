from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai import gateway as ai_gateway
from app.api.deps import get_ai_gateway, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import ExplanationRequest, ExplanationResponse
from app.services import explanation_service

router = APIRouter(prefix="/ai")


@router.post("/explanations", response_model=ExplanationResponse)
def create_explanation(
    payload: ExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gateway: ai_gateway.AIGateway = Depends(get_ai_gateway),
) -> ExplanationResponse:
    """No role restriction — any authenticated tenant member, including
    STUDENT, may request an explanation (ADR-015 §6: no review-gate in this
    slice)."""
    try:
        return explanation_service.generate_skill_explanation(
            db,
            gateway=gateway,
            tenant_id=current_user.tenant_id,
            actor_user_id=current_user.id,
            skill_id=payload.skill_id,
        )
    except explanation_service.SkillNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill_not_found")
    except ai_gateway.SchemaValidationError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="ai_provider_returned_invalid_output")
    except ai_gateway.SafetyRejected:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="ai_output_failed_safety_check")
    except ai_gateway.ProviderFailed:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ai_provider_unavailable")

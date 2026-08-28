"""AI Gateway orchestration (ADR-015). The single path from application
code to an LLM call: renders a versioned prompt, calls the injected
provider, validates the result against the prompt's schema (§47), runs a
minimal safety check (§82), and persists an AIUsageRecord on every exit
path — success or failure — before returning or raising.
"""
import json
import time

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.ai.prompts import PromptTemplate
from app.ai.providers.base import AIProvider, GenerationRequest, ProviderError
from app.ai.safety import SafetyViolation, validate_output_safety
from app.models.ai_usage import AIUsageCapability, AIUsageRecord


class AIGatewayError(Exception):
    pass


class SchemaValidationError(AIGatewayError):
    """The model's output did not parse as JSON, or didn't match the
    requested schema — §47 "reject malformed output," never coerced."""


class SafetyRejected(AIGatewayError):
    pass


class ProviderFailed(AIGatewayError):
    """Wraps a ProviderError so callers never need to know provider-specific
    exception types (§43 — business logic must not depend on a provider)."""


class AIGateway:
    def __init__(self, *, provider: AIProvider, db: Session) -> None:
        self._provider = provider
        self.db = db

    @property
    def provider(self) -> AIProvider:
        return self._provider

    def generate(
        self,
        *,
        template: PromptTemplate,
        prompt_kwargs: dict,
        tenant_id: str,
        actor_user_id: str,
        capability: AIUsageCapability,
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> BaseModel:
        prompt = template.render(**prompt_kwargs)
        request = GenerationRequest(
            prompt=prompt, response_schema=template.response_schema, max_tokens=max_tokens, temperature=temperature
        )

        started_at = time.monotonic()
        try:
            result = self._provider.generate(request)
        except ProviderError as exc:
            self._record_usage(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                capability=capability,
                template=template,
                input_tokens=None,
                output_tokens=None,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                success=False,
                error_reason=type(exc).__name__,
            )
            raise ProviderFailed(str(exc)) from exc

        try:
            parsed = template.response_schema.model_validate_json(result.raw_text)
        except (ValidationError, json.JSONDecodeError) as exc:
            self._record_usage(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                capability=capability,
                template=template,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                latency_ms=result.latency_ms,
                success=False,
                error_reason=type(exc).__name__,
            )
            raise SchemaValidationError("model output did not match the requested schema") from exc

        try:
            for field_name in parsed.model_fields:
                value = getattr(parsed, field_name)
                if isinstance(value, str):
                    validate_output_safety(value)
        except SafetyViolation as exc:
            self._record_usage(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                capability=capability,
                template=template,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                latency_ms=result.latency_ms,
                success=False,
                error_reason="safety_violation",
            )
            raise SafetyRejected(str(exc)) from exc

        self._record_usage(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            capability=capability,
            template=template,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            success=True,
            error_reason=None,
        )
        return parsed

    def _record_usage(
        self,
        *,
        tenant_id: str,
        actor_user_id: str,
        capability: AIUsageCapability,
        template: PromptTemplate,
        input_tokens: int | None,
        output_tokens: int | None,
        latency_ms: int,
        success: bool,
        error_reason: str | None,
    ) -> None:
        self.db.add(
            AIUsageRecord(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                provider=self._provider.provider_name,
                model=self._provider.model_name,
                capability=capability,
                prompt_name=template.name,
                prompt_version=template.version,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                success=success,
                error_reason=(error_reason[:200] if error_reason else None),
            )
        )
        self.db.commit()

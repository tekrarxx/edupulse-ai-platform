import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.assessment import router as assessment_router
from app.api.routes.auth import router as auth_router
from app.api.routes.curriculum import router as curriculum_router
from app.api.routes.decision import router as decision_router
from app.api.routes.health import router as health_router
from app.api.routes.knowledge_state import router as knowledge_state_router
from app.api.routes.retention import router as retention_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.environment)
logger = logging.getLogger(__name__)

app = FastAPI(title="EduPulse AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak stack traces, SQL errors, or internal paths to clients (§90)."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal_server_error"})


app.include_router(health_router, tags=["health"])
app.include_router(auth_router, tags=["auth"])
app.include_router(curriculum_router, tags=["curriculum"])
app.include_router(assessment_router, tags=["assessment"])
app.include_router(knowledge_state_router, tags=["knowledge-state"])
app.include_router(decision_router, tags=["decisions"])
app.include_router(retention_router, tags=["retention"])

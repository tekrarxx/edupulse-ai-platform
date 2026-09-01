import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes.ai import router as ai_router
from app.api.routes.assessment import router as assessment_router
from app.api.routes.auth import router as auth_router
from app.api.routes.curriculum import router as curriculum_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.decision import router as decision_router
from app.api.routes.health import router as health_router
from app.api.routes.knowledge_state import router as knowledge_state_router
from app.api.routes.plan import router as plan_router
from app.api.routes.retention import router as retention_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metrics import http_request_duration_seconds, http_requests_total
from app.core.request_context import get_request_id, new_request_id, set_request_id

settings = get_settings()
configure_logging(settings.environment)
logger = logging.getLogger(__name__)
_REQUEST_ID_HEADER = "X-Request-ID"

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
    """Never leak stack traces, SQL errors, or internal paths to clients
    (§90) — but `request_id` is not an internal detail, it is specifically
    meant to be handed back so a support report can be correlated to the
    matching structured log line (§83)."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal_server_error", "request_id": get_request_id()})


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """§83 traces + access log. Accepts a caller-supplied `X-Request-ID`
    (so a request can be correlated across this API and an upstream/gateway
    that already minted one) or mints a fresh one; either way it is echoed
    back on the response and available to every log line emitted while
    handling this request (app/core/request_context.py). Also emits exactly
    one structured access-log line per request — method, route template,
    status, duration — which nothing in this codebase produced before this
    slice (only errors were previously logged, never successful requests)."""
    request_id = request.headers.get(_REQUEST_ID_HEADER) or new_request_id()
    set_request_id(request_id)

    started_at = time.perf_counter()
    response = await call_next(request)
    duration_seconds = time.perf_counter() - started_at

    route = request.scope.get("route")
    # An unmatched path (404, or a probing/scanning request) has no route
    # object — label it as a fixed literal, never the raw path, or the
    # metric becomes unbounded-cardinality (see app/core/metrics.py).
    route_template = route.path if route is not None else "unmatched"

    http_requests_total.labels(method=request.method, route=route_template, status_code=str(response.status_code)).inc()
    http_request_duration_seconds.labels(method=request.method, route=route_template).observe(duration_seconds)

    logger.info(
        "request",
        extra={
            "http_method": request.method,
            "http_route": route_template,
            "http_status_code": response.status_code,
            "duration_ms": round(duration_seconds * 1000, 2),
        },
    )

    response.headers[_REQUEST_ID_HEADER] = request_id
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """§78 baseline security headers. This is a JSON API, not an HTML
    renderer, so `Content-Security-Policy: default-src 'none'` is a correct
    default rather than a compromise — there is no first-party page here for
    a broken policy to break. HSTS is safe to always send even from plain
    HTTP in local development: browsers only start enforcing it after they
    have seen it once over a real HTTPS connection, so it does nothing until
    a production deployment actually serves over TLS (§120 cloud migration:
    an infra concern, not an application-logic branch on environment)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """§83. Unauthenticated, matching /health's existing risk posture — the
    payload is request counts/latencies by route template only, nothing
    learner- or tenant-identifying (§84). A real deployment should still
    restrict this at the network/infra layer (an unauthenticated ops
    endpoint reachable from the public internet is unnecessary exposure),
    which is an infra-adapter concern (§120), not application code."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(health_router, tags=["health"])
app.include_router(auth_router, tags=["auth"])
app.include_router(curriculum_router, tags=["curriculum"])
app.include_router(assessment_router, tags=["assessment"])
app.include_router(knowledge_state_router, tags=["knowledge-state"])
app.include_router(decision_router, tags=["decisions"])
app.include_router(retention_router, tags=["retention"])
app.include_router(ai_router, tags=["ai"])
app.include_router(dashboard_router, tags=["dashboard"])
app.include_router(plan_router, tags=["plans"])

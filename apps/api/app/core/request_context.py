"""Per-request correlation id (§83 Traces / §85 "who, when" tracing).

A contextvar rather than request.state because app/core/logging.py's
formatter needs it inside a plain `logging.Filter`, which only ever sees a
`LogRecord` — not the `Request` object — so a global (but request-scoped,
via contextvars' async-safe isolation) lookup is the only way a log line
emitted deep inside a service function can carry the id without threading
an extra parameter through every function signature in the codebase.
"""
import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()

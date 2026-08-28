import logging
import sys

_SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "api_key"}


class RedactSensitiveFieldsFilter(logging.Filter):
    """Defense-in-depth: refuses to emit a record whose message text contains
    an obvious secret-shaped key=value pair (§84 — never log passwords,
    tokens, API keys, or learner-sensitive data)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        for key in _SENSITIVE_KEYS:
            if f"{key}=" in message or f'"{key}"' in message:
                record.msg = "[redacted: potential sensitive field in log message]"
                record.args = ()
                break
        return True


def configure_logging(environment: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactSensitiveFieldsFilter())
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if environment == "development" else logging.INFO)

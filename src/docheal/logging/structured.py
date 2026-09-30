import json
import logging
import sys
import uuid
from typing import Any


def _sensitive_key(key: object) -> bool:
    normalized = str(key).lower()
    return normalized in {"token", "github_token", "api_key", "openai_api_key", "authorization"} or normalized.endswith("_secret")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _sensitive_key(key) else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"level": record.levelname, "logger": record.name, "message": record.getMessage()}
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> str:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("docheal")
    root.handlers[:] = [handler]
    root.setLevel(level)
    return str(uuid.uuid4())


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    safe = _sanitize(fields)
    logger.info(event, extra={"fields": {"event": event, **safe}})

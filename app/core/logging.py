import logging
import re
import sys
from app.core.config import settings

_SENSITIVE_KV_PATTERN = re.compile(
    r"(?i)(['\"]?(?:api[_-]?key|apikey|secret(?:[_-]?key)?|access[_-]?token|auth[_-]?token|token|password|authorization)['\"]?\s*[:=]\s*['\"]?)(Bearer\s+)?([^\s,'\"\}]+)",
)
_BEARER_PATTERN = re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9\-._~+/]+=*)")
_KNOWN_TOKEN_PATTERN = re.compile(
    r"(?:AIza[0-9A-Za-z\-_]{20,}|ghp_[0-9A-Za-z]{20,}|sk-[0-9A-Za-z]{20,})"
)


def redact_secrets(text: str) -> str:
    """Redact API keys, tokens, secrets, passwords, and Bearer credentials from log strings."""
    if not isinstance(text, str) or not text:
        return text
    redacted = _SENSITIVE_KV_PATTERN.sub(r"\1\2[REDACTED]", text)
    redacted = _BEARER_PATTERN.sub(r"\1[REDACTED]", redacted)
    redacted = _KNOWN_TOKEN_PATTERN.sub("[REDACTED]", redacted)
    return redacted


class SecretRedactingFilter(logging.Filter):
    """Logging filter that sanitizes sensitive key/token patterns before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            formatted = record.getMessage()
            record.msg = redact_secrets(formatted)
            record.args = None
        except Exception:
            if isinstance(record.msg, str):
                record.msg = redact_secrets(record.msg)
        return True


def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(SecretRedactingFilter())
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[handler],
    )
    app_logger = logging.getLogger("app")
    app_logger.addFilter(SecretRedactingFilter())
    return app_logger


logger = setup_logging()

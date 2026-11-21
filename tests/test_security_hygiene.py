"""
Security & API Key Hygiene Tests
================================
Verifies:
1. .gitignore covers .env, key/pem/credential files, and secrets/ while allowing .env.example.
2. .env.example contains only non-secret defaults and obvious placeholders.
3. app.core.config.Settings does not hardcode external secret values.
4. app.core.logging.redact_secrets & SecretRedactingFilter sanitize sensitive tokens.
"""

import logging
import re
from pathlib import Path

from app.core.config import Settings
from app.core.logging import SecretRedactingFilter, redact_secrets

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_gitignore_covers_secret_patterns():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    lines = {line.strip() for line in gitignore.splitlines() if line.strip() and not line.strip().startswith("#")}
    required = {
        ".env",
        ".env.*",
        "!.env.example",
        "*.pem",
        "*.key",
        "*credentials*.json",
        "*service-account*.json",
        "secrets/",
    }
    missing = required - lines
    assert not missing, f".gitignore missing required secret patterns: {missing}"


def test_env_example_has_only_placeholders():
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    # Must not contain real token signatures
    forbidden_patterns = [
        r"AIza[0-9A-Za-z\-_]{20,}",
        r"ghp_[0-9A-Za-z]{20,}",
        r"sk-[0-9A-Za-z]{20,}",
        r"-----BEGIN .*PRIVATE KEY-----",
    ]
    for pat in forbidden_patterns:
        assert not re.search(pat, env_example), f".env.example matched forbidden secret pattern: {pat}"

    # Any KEY/SECRET/TOKEN entry must use an obvious placeholder
    for line in env_example.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        if any(s in key.upper() for s in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
            assert val == "" or "YOUR_" in val.upper() or "PLACEHOLDER" in val.upper(), (
                f".env.example key {key} must use an obvious placeholder, got non-placeholder value"
            )


def test_settings_external_secrets_default_to_none(monkeypatch):
    for var in ("NASA_POWER_API_KEY", "COPERNICUS_CLIENT_ID", "COPERNICUS_CLIENT_SECRET", "EARTHDATA_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    fresh = Settings(_env_file=None)
    assert fresh.NASA_POWER_API_KEY is None
    assert fresh.COPERNICUS_CLIENT_ID is None
    assert fresh.COPERNICUS_CLIENT_SECRET is None
    assert fresh.EARTHDATA_TOKEN is None


def test_redact_secrets_sanitizes_sensitive_values():
    sample = (
        "Calling API with api_key=demo_val_123, "
        "authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig, "
        '{"secret": "my_dummy_secret", "password": "pass_value"} '
        "and normal_metric=0.95"
    )
    cleaned = redact_secrets(sample)
    assert "demo_val_123" not in cleaned
    assert "eyJhbGciOiJIUzI1NiJ9" not in cleaned
    assert "my_dummy_secret" not in cleaned
    assert "pass_value" not in cleaned
    assert "[REDACTED]" in cleaned
    assert "normal_metric=0.95" in cleaned


def test_secret_redacting_filter_on_logger(caplog):
    test_logger = logging.getLogger("test_security_redaction")
    test_logger.setLevel(logging.INFO)
    filt = SecretRedactingFilter()
    test_logger.addFilter(filt)
    try:
        with caplog.at_level(logging.INFO, logger="test_security_redaction"):
            test_logger.info("Request failed with token=%s for plot=%s", "dummy_tok_999", "Plot-1")
        assert "dummy_tok_999" not in caplog.text
        assert "[REDACTED]" in caplog.text
        assert "Plot-1" in caplog.text
    finally:
        test_logger.removeFilter(filt)

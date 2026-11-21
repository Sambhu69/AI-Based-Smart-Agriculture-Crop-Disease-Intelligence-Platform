import pytest
from app.core.config import Settings

def test_config_defaults():
    s = Settings()
    assert s.APP_NAME == "Smart Agriculture Platform"
    assert s.APP_ENV == "development"
    assert s.LOG_LEVEL == "INFO"
    assert s.MODEL_VERSION == "1.1.0"
    assert s.MODEL_ARCHITECTURE == "resnet50"
    assert s.IMAGE_SIZE == 224
    assert len(s.DEFAULT_CLASS_NAMES) == 15
    assert "Tomato_healthy" in s.DEFAULT_CLASS_NAMES

def test_config_override_env(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Custom Ag Platform")
    monkeypatch.setenv("MODEL_VERSION", "2.0.0")
    s = Settings()
    assert s.APP_NAME == "Custom Ag Platform"
    assert s.MODEL_VERSION == "2.0.0"

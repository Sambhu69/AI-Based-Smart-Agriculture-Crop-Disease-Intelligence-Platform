import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Smart Agriculture Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # SQLite default avoids requiring external DBMS during early stages
    DATABASE_URL: str = "sqlite:///./smart_ag.db"

    # Inference & Model Provenance
    MODEL_CHECKPOINT_PATH: str = "models/best_model.pth"
    MODEL_VERSION: str = "1.1.0"
    MODEL_ARCHITECTURE: str = "resnet50"
    IMAGE_SIZE: int = 224
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB
    DEFAULT_DEVICE: str = "cuda"

    # Default supported classes for PlantVillage disease classifier
    DEFAULT_CLASS_NAMES: List[str] = [
        "Pepper__bell___Bacterial_spot",
        "Pepper__bell___healthy",
        "Potato___Early_blight",
        "Potato___Late_blight",
        "Potato___healthy",
        "Tomato_Bacterial_spot",
        "Tomato_Early_blight",
        "Tomato_Late_blight",
        "Tomato_Leaf_Mold",
        "Tomato_Septoria_leaf_spot",
        "Tomato_Spider_mites_Two_spotted_spider_mite",
        "Tomato__Target_Spot",
        "Tomato__Tomato_YellowLeaf__Curl_Virus",
        "Tomato__Tomato_mosaic_virus",
        "Tomato_healthy",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()

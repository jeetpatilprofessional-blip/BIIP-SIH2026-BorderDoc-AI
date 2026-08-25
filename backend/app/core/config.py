# BIIP-SIH2026 Core Configuration
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "BIIP"
    APP_VERSION: str = "1.0.0-sih2026"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Backend
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./biip.db"

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Model Paths
    MODEL_DIR: str = "./models"

    # OCR
    PADDLE_OCR_LANG: str = "en"
    PADDLE_OCR_USE_GPU: bool = False

    # Face Recognition
    INSIGHTFACE_MODEL_PATH: str = "./models/insightface/buffalo_l/w600k_r50.onnx"
    INSIGHTFACE_DET_MODEL_PATH: str = "./models/insightface/buffalo_l/det_10g.onnx"
    FACE_EMBEDDING_DIM: int = 512
    FACE_MATCH_THRESHOLD: float = 0.35
    FACE_QUALITY_THRESHOLD: float = 0.5

    # Liveness
    LIVENESS_ENABLED: bool = True
    LIVENESS_THRESHOLD: float = 0.6

    # MRZ
    MRZ_ENABLED: bool = True

    # Barcode/QR
    BARCODE_ENABLED: bool = True

    # Freshness Policies (hours)
    FRESHNESS_WATCHLIST_HOURS: int = 6
    FRESHNESS_VISA_HOURS: int = 24
    FRESHNESS_PASSPORT_HOURS: int = 168
    FRESHNESS_NATIONAL_ID_HOURS: int = 168

    # Offline Mode
    OFFLINE_MODE: bool = False
    SYNC_INTERVAL_SECONDS: int = 300

    # Simulated Central Service
    CENTRAL_SERVICE_ENABLED: bool = True
    CENTRAL_SERVICE_URL: str = "http://localhost:8001"
    CENTRAL_SERVICE_SIMULATED: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    API_KEY_HEADER: str = "X-API-Key"

    # Demo
    DEMO_MODE: bool = True
    DETERMINISTIC_SEED: int = 42

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
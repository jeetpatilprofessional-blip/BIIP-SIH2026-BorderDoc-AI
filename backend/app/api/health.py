# BIIP-SIH2026 Health API
from fastapi import APIRouter
from datetime import datetime
from app.schemas.system import HealthCheck
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("", response_model=HealthCheck)
async def health_check():
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.APP_VERSION,
    )


@router.get("/ready")
async def readiness_check():
    return {"status": "ready", "timestamp": datetime.utcnow()}
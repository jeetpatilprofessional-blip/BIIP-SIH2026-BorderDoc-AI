# BIIP-SIH2026 Main FastAPI Application
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys

from app.core.config import get_settings
from app.core.database import init_db, engine
from app.api import cases, documents, evidence, recommendation, system, sync, health, demo, audit, identity_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Border Identity Intelligence Platform - SIH 2026",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(documents.router, prefix="/api/cases", tags=["Documents"])
app.include_router(evidence.router, prefix="/api/cases", tags=["Evidence"])
app.include_router(recommendation.router, prefix="/api/cases", tags=["Recommendation"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(sync.router, prefix="/api/sync", tags=["Sync"])
app.include_router(demo.router, prefix="/api", tags=["Demo"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(identity_graph.router, prefix="/api/identity-graph", tags=["Identity Graph"])
app.include_router(identity_graph.router, prefix="/api/cases", tags=["Identity Graph Cases Alias"])



@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Border Identity Intelligence Platform - SIH 2026",
        "status": "running",
    }
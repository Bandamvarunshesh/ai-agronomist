from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.health_checks import validate_startup_or_raise
from app.core.logging import configure_logging
from app.core.config import settings
from app.api.v1.router import api_router
from app.services.intelligence_scheduler import intelligence_scheduler


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_report = validate_startup_or_raise()
    app.state.startup_report = startup_report
    logger.info(
        "Application startup validation succeeded: environment=%s database=%s pgvector=%s storage=%s gemini_configured=%s",
        settings.environment,
        startup_report["database"]["status"],
        startup_report["pgvector"]["status"],
        startup_report["storage"]["status"],
        settings.is_gemini_configured,
    )
    intelligence_scheduler.start()
    try:
        yield
    finally:
        await intelligence_scheduler.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        access_log=settings.log_access,
    )

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.services.intelligence_scheduler import intelligence_scheduler


logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router)


@app.on_event("startup")
async def log_gemini_configuration() -> None:
    """Temporary startup log for Gemini configuration status."""
    configured = "Yes" if settings.is_gemini_configured else "No"
    logger.info("Gemini configured: %s", configured)
    intelligence_scheduler.start()


@app.on_event("shutdown")
async def stop_background_jobs() -> None:
    await intelligence_scheduler.stop()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

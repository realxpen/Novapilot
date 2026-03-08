"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.routes import router as api_router
from app.config import get_settings
from app.utils.logger import get_logger


settings = get_settings()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Application factory for NovaPilot backend."""
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(api_router)

    @app.on_event("startup")
    def startup_log() -> None:
        logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    return app


app = create_app()

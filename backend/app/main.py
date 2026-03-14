"""FastAPI application entrypoint."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import BACKEND_ROOT, REPO_ROOT, get_settings
from app.utils.logger import get_logger
from app.utils.secrets import mask_secret


settings = get_settings()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Application factory for NovaPilot backend."""
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.on_event("startup")
    def startup_log() -> None:
        logger.info(
            "Starting %s v%s | live_nova_act_enabled=%s | strict_live_mode=%s | fallback_to_mock_on_live_failure=%s | nova_api_key_present=%s | masked_nova_api_key=%s | backend_env=%s | repo_env=%s | os_environ_has_nova_act_api_key=%s | os_environ_has_nova_api_key=%s | settings_cached=%s",
            settings.app_name,
            settings.app_version,
            settings.use_nova_act_automation,
            settings.nova_act_strict_mode,
            settings.fallback_to_mock_on_live_failure,
            bool(settings.nova_api_key),
            mask_secret(settings.nova_api_key),
            str(BACKEND_ROOT / ".env"),
            str(REPO_ROOT / ".env"),
            bool(os.environ.get("NOVA_ACT_API_KEY")),
            bool(os.environ.get("NOVA_API_KEY")),
            True,
        )
        logger.info(
            "NOVAPILOT_STARTUP_FLAGS live_nova_act_enabled=%s fallback_to_mock_on_live_failure=%s nova_act_timeout_seconds=%s nova_api_key_present=%s masked_nova_api_key=%s",
            settings.use_nova_act_automation,
            settings.fallback_to_mock_on_live_failure,
            settings.nova_act_timeout_seconds,
            bool(settings.nova_api_key),
            mask_secret(settings.nova_api_key),
        )
        if settings.use_nova_act_automation and not settings.nova_api_key:
            logger.warning(
                "Live Nova Act automation is enabled, but no Nova API key was loaded. "
                "Set NOVA_ACT_API_KEY or NOVA_API_KEY in backend/.env and restart the backend."
            )

    return app


app = create_app()

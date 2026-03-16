"""Application configuration loaded from environment variables."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, List, Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime settings for the NovaPilot backend."""

    model_config = SettingsConfigDict(
        env_prefix="NOVAPILOT_",
        case_sensitive=False,
        env_file=(str(BACKEND_ROOT / ".env"), str(REPO_ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NovaPilot Backend"
    app_version: str = "0.1.0"
    nova_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("NOVA_API_KEY", "NOVA_ACT_API_KEY", "nova_api_key"),
    )
    aws_access_key_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "AWS_ACCESS_KEY_ID",
            "NOVAPILOT_AWS_ACCESS_KEY_ID",
            "aws_access_key_id",
        ),
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "AWS_SECRET_ACCESS_KEY",
            "NOVAPILOT_AWS_SECRET_ACCESS_KEY",
            "aws_secret_access_key",
        ),
    )
    aws_session_token: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "AWS_SESSION_TOKEN",
            "NOVAPILOT_AWS_SESSION_TOKEN",
            "aws_session_token",
        ),
    )
    aws_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("AWS_REGION", "NOVAPILOT_AWS_REGION", "aws_region"),
    )
    usd_to_ngn_rate: float = Field(
        default=1600.0,
        validation_alias=AliasChoices("USD_TO_NGN_RATE", "NOVAPILOT_USD_TO_NGN_RATE", "usd_to_ngn_rate"),
    )
    default_supported_sites: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["jumia"]
    )
    default_currency: str = "NGN"
    log_level: str = "INFO"
    cors_allow_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        validation_alias=AliasChoices(
            "CORS_ALLOW_ORIGINS",
            "NOVAPILOT_CORS_ALLOW_ORIGINS",
            "cors_allow_origins",
        ),
    )
    cors_allow_origin_regex: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "CORS_ALLOW_ORIGIN_REGEX",
            "NOVAPILOT_CORS_ALLOW_ORIGIN_REGEX",
            "cors_allow_origin_regex",
        ),
    )
    use_bedrock_interpretation: bool = False
    use_bedrock_report_generation: bool = False
    use_bedrock_site_selection: bool = True
    use_nova_act_automation: bool = True
    nova_act_strict_mode: bool = True
    bedrock_interpret_model_id: str = "amazon.nova-lite-v1:0"
    bedrock_report_model_id: str = "amazon.nova-lite-v1:0"
    bedrock_site_selection_model_id: str = "amazon.nova-lite-v1:0"
    nova_act_timeout_seconds: int = 180
    nova_act_poll_interval_seconds: float = 2.0
    jobs_storage_path: str = str(BACKEND_ROOT / ".novapilot_jobs.json")

    @field_validator("default_supported_sites", mode="before")
    @classmethod
    def parse_supported_sites(cls, value: object) -> object:
        """Allow JSON arrays or comma-separated env var values for supported sites."""
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.startswith("["):
                try:
                    parsed = json.loads(normalized)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(site).strip().lower() for site in parsed if str(site).strip()]
            return [site.strip().lower() for site in value.split(",") if site.strip()]
        return value

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: object) -> object:
        """Allow JSON arrays or comma-separated env var values for CORS origins."""
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.startswith("["):
                try:
                    parsed = json.loads(normalized)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance.

    Settings are loaded once per backend process. Restart the backend to reload
    changes made to backend/.env, repo .env, or shell-provided environment vars.
    """
    return Settings()

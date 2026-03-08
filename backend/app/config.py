"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the NovaPilot backend."""

    model_config = SettingsConfigDict(env_prefix="NOVAPILOT_", case_sensitive=False)

    app_name: str = "NovaPilot Backend"
    app_version: str = "0.1.0"
    default_supported_sites: List[str] = Field(default_factory=lambda: ["jumia", "amazon"])
    default_currency: str = "NGN"
    log_level: str = "INFO"
    use_bedrock_interpretation: bool = False
    use_bedrock_report_generation: bool = False
    use_nova_act_automation: bool = False

    @field_validator("default_supported_sites", mode="before")
    @classmethod
    def parse_supported_sites(cls, value: object) -> object:
        """Allow comma-separated env var values for supported sites."""
        if isinstance(value, str):
            return [site.strip().lower() for site in value.split(",") if site.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()

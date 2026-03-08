"""Request schemas for NovaPilot API routes."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class RunNovaPilotRequest(BaseModel):
    """Input payload for running the NovaPilot pipeline."""

    query: str = Field(..., min_length=5, description="Natural-language shopping query")
    supported_sites: List[str] = Field(default_factory=lambda: ["jumia", "amazon"])
    top_n: int = Field(default=3, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("query must not be empty")
        return clean

    @field_validator("supported_sites")
    @classmethod
    def normalize_sites(cls, value: List[str]) -> List[str]:
        cleaned = [site.strip().lower() for site in value if site.strip()]
        return cleaned or ["jumia", "amazon"]

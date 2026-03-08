"""Pydantic schema for normalized product objects."""

from typing import Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    """Unified product model used across extraction, ranking, and reporting."""

    name: str
    store: str
    price: float
    currency: str
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    cpu: Optional[str] = None
    gpu: Optional[str] = None
    screen_size: Optional[str] = None
    url: Optional[str] = None
    score: Optional[float] = None
    image_url: Optional[str] = None
    short_reason: Optional[str] = None

"""Logging helpers for consistent application logging."""

import logging

from app.config import get_settings


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger(name)

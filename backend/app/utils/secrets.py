"""Helpers for masking secrets in logs."""

from __future__ import annotations


def mask_secret(value: str | None) -> str | None:
    """Return a masked representation of a secret value."""
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"

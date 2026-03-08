"""Helpers for normalizing raw scraped/mock data."""

import re
from typing import Optional


def normalize_currency(value: Optional[str]) -> str:
    """Normalize currency symbols/codes to a canonical code."""
    if not value:
        return "NGN"
    raw = value.strip().upper()
    mapping = {"₦": "NGN", "NGN": "NGN", "$": "USD", "USD": "USD"}
    return mapping.get(raw, raw)


def parse_price(price_value: object) -> float:
    """Parse string or numeric price into float. Returns 0.0 on failure."""
    if isinstance(price_value, (int, float)):
        return float(price_value)
    if not isinstance(price_value, str):
        return 0.0
    digits = re.sub(r"[^\d.]", "", price_value)
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


def extract_ram_gb(text: Optional[str]) -> Optional[int]:
    """Extract RAM in GB from free text."""
    if not text:
        return None
    match = re.search(r"(\d+)\s*GB\s*RAM", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def extract_storage_gb(text: Optional[str]) -> Optional[int]:
    """Extract storage capacity in GB from free text."""
    if not text:
        return None
    gb_match = re.search(r"(\d+)\s*GB\s*(SSD|HDD|STORAGE)", text, flags=re.IGNORECASE)
    tb_match = re.search(r"(\d+)\s*TB", text, flags=re.IGNORECASE)
    if tb_match:
        return int(tb_match.group(1)) * 1024
    if gb_match:
        return int(gb_match.group(1))
    # Fallback: pick GB values that are not RAM labels.
    gb_values = re.findall(r"(\d+)\s*GB(?!\s*RAM)", text, flags=re.IGNORECASE)
    if gb_values:
        return int(gb_values[-1])
    return None


def extract_screen_size(text: Optional[str]) -> Optional[str]:
    """Extract screen size from free text."""
    if not text:
        return None
    match = re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:\"|INCH)", text, flags=re.IGNORECASE)
    return f"{match.group(1)} inch" if match else None

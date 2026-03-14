"""Helpers for normalizing raw scraped/mock data."""

import re
from typing import Optional


def normalize_currency(value: Optional[str]) -> str:
    """Normalize currency symbols/codes to a canonical code."""
    if not value:
        return "NGN"
    raw = value.strip().upper()
    if "NGN" in raw or "NAIRA" in raw or "\u20A6" in value or "â‚¦" in value:
        return "NGN"
    if raw == "$" or "USD" in raw:
        return "USD"
    if re.fullmatch(r"[A-Z]{3}", raw):
        return raw
    return "NGN"


def parse_price(price_value: object) -> float:
    """Parse string or numeric price into float. Returns 0.0 on failure."""
    if isinstance(price_value, (int, float)):
        return float(price_value)
    if not isinstance(price_value, str):
        return 0.0

    matches = re.findall(r"\d[\d,]*(?:\.\d+)?", price_value)
    if not matches:
        return 0.0

    parsed_values: list[float] = []
    for token in matches:
        try:
            parsed_values.append(float(token.replace(",", "")))
        except ValueError:
            continue

    if not parsed_values:
        return 0.0

    for value in parsed_values:
        if value >= 1:
            return value
    return parsed_values[0]


def extract_ram_gb(text: Optional[str]) -> Optional[int]:
    """Extract RAM in GB from free text."""
    if not text:
        return None

    explicit_match = re.search(r"(\d{1,3})\s*GB\s*(?:RAM|MEMORY)\b", text, flags=re.IGNORECASE)
    if explicit_match:
        return int(explicit_match.group(1))

    pair_match = re.search(
        r"(\d{1,3})\s*GB\s*(?:[/+]|AND)\s*(\d{1,4})\s*GB",
        text,
        flags=re.IGNORECASE,
    )
    if pair_match:
        first, second = int(pair_match.group(1)), int(pair_match.group(2))
        return first if first <= second else second

    reverse_pair_match = re.search(
        r"(\d{1,4})\s*GB\s*/\s*(\d{1,3})\s*GB",
        text,
        flags=re.IGNORECASE,
    )
    if reverse_pair_match:
        first, second = int(reverse_pair_match.group(1)), int(reverse_pair_match.group(2))
        return second if second <= first else first

    gb_values = [int(v) for v in re.findall(r"(\d{1,4})\s*GB", text, flags=re.IGNORECASE)]
    if len(gb_values) >= 2:
        return min(gb_values)
    if gb_values and gb_values[0] <= 64:
        return gb_values[0]
    return None


def extract_storage_gb(text: Optional[str]) -> Optional[int]:
    """Extract storage capacity in GB from free text."""
    if not text:
        return None

    explicit_match = re.search(
        r"(\d{2,4})\s*GB\s*(?:SSD|HDD|STORAGE|ROM|UFS)\b",
        text,
        flags=re.IGNORECASE,
    )
    if explicit_match:
        return int(explicit_match.group(1))

    pair_match = re.search(
        r"(\d{1,3})\s*GB\s*(?:[/+]|AND)\s*(\d{2,4})\s*GB",
        text,
        flags=re.IGNORECASE,
    )
    if pair_match:
        return int(pair_match.group(2))

    reverse_pair_match = re.search(
        r"(\d{2,4})\s*GB\s*/\s*(\d{1,3})\s*GB",
        text,
        flags=re.IGNORECASE,
    )
    if reverse_pair_match:
        return int(reverse_pair_match.group(1))

    tb_match = re.search(r"(\d+)\s*TB", text, flags=re.IGNORECASE)
    if tb_match:
        return int(tb_match.group(1)) * 1024

    gb_values = [int(v) for v in re.findall(r"(\d{1,4})\s*GB(?!\s*RAM)", text, flags=re.IGNORECASE)]
    large_values = [v for v in gb_values if v >= 64]
    if large_values:
        return max(large_values)
    return None


def extract_screen_size(text: Optional[str]) -> Optional[str]:
    """Extract screen size from free text."""
    if not text:
        return None
    match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:\"|INCH)", text, flags=re.IGNORECASE)
    return f"{match.group(1)} inch" if match else None

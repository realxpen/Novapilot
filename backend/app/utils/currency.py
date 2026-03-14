"""Currency conversion helpers used across automation, filtering, and ranking."""

from __future__ import annotations

from typing import Optional


def normalize_currency_code(value: str | None) -> str | None:
    if not value:
        return None
    code = str(value).strip().upper()
    if not code:
        return None
    if code in {"$", "USD", "US$"}:
        return "USD"
    if code in {"NGN", "₦", "NAIRA"}:
        return "NGN"
    return code


def convert_amount(
    amount: float | None,
    from_currency: str | None,
    to_currency: str | None,
    usd_to_ngn_rate: float,
) -> Optional[float]:
    """Convert between NGN and USD using a configurable runtime rate."""
    if amount is None:
        return None

    source = normalize_currency_code(from_currency)
    target = normalize_currency_code(to_currency)
    if not source or not target:
        return None
    if source == target:
        return float(amount)

    if source == "NGN" and target == "USD":
        return float(amount) / usd_to_ngn_rate
    if source == "USD" and target == "NGN":
        return float(amount) * usd_to_ngn_rate
    return None


def site_budget_currency(site: str) -> str:
    """Return the default listing currency used for a supported store."""
    return "USD" if site.strip().lower() == "amazon" else "NGN"

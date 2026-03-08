"""Scoring helpers for the ranking layer."""

from typing import Optional


def budget_score(price: float, budget_max: Optional[float]) -> float:
    """Score budget fit from 0-10."""
    if not budget_max or budget_max <= 0:
        return 5.0
    if price <= budget_max:
        return max(1.0, 10.0 - ((budget_max - price) / budget_max) * 2.0)
    over_pct = (price - budget_max) / budget_max
    return max(0.0, 6.0 - over_pct * 20.0)


def ram_score(ram_gb: Optional[int]) -> float:
    """Score RAM adequacy from 0-10."""
    if ram_gb is None:
        return 3.0
    if ram_gb >= 32:
        return 10.0
    if ram_gb >= 16:
        return 8.5
    if ram_gb >= 8:
        return 6.5
    return 4.0


def storage_score(storage_gb: Optional[int]) -> float:
    """Score storage adequacy from 0-10."""
    if storage_gb is None:
        return 3.0
    if storage_gb >= 1024:
        return 10.0
    if storage_gb >= 512:
        return 8.0
    if storage_gb >= 256:
        return 6.5
    return 4.0


def rating_score(rating: Optional[float]) -> float:
    """Convert rating (0-5) to 0-10 score."""
    if rating is None:
        return 5.0
    return max(0.0, min(10.0, rating * 2.0))


def cpu_score(cpu: Optional[str]) -> float:
    """Simple CPU strength heuristic from 0-10."""
    if not cpu:
        return 4.0
    cpu_name = cpu.lower()
    strong_tokens = ("i9", "i7", "ryzen 9", "ryzen 7", "m3", "m2")
    medium_tokens = ("i5", "ryzen 5", "m1")
    weak_tokens = ("i3", "celeron", "pentium", "athlon")
    if any(token in cpu_name for token in strong_tokens):
        return 9.0
    if any(token in cpu_name for token in medium_tokens):
        return 7.0
    if any(token in cpu_name for token in weak_tokens):
        return 4.0
    return 6.0


def gpu_score(gpu: Optional[str]) -> float:
    """Simple GPU strength heuristic from 0-10."""
    if not gpu:
        return 4.0
    gpu_name = gpu.lower()
    strong_tokens = ("rtx 40", "rtx 30", "rx 7", "rx 6")
    medium_tokens = ("gtx 16", "rtx 20", "intel arc")
    weak_tokens = ("integrated", "uhd", "iris", "vega")
    if any(token in gpu_name for token in strong_tokens):
        return 9.0
    if any(token in gpu_name for token in medium_tokens):
        return 7.0
    if any(token in gpu_name for token in weak_tokens):
        return 5.0
    return 6.0


def value_score(price: float, quality_score: float) -> float:
    """Approximate value-for-money score from 0-10."""
    if price <= 0:
        return 0.0
    normalized = (quality_score * 100000) / price
    return max(0.0, min(10.0, normalized))

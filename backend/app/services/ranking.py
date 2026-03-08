"""Transparent product ranking engine."""

from typing import Dict, List

from app.schemas.product import Product
from app.schemas.response import InterpretedRequest
from app.services.ranking_weights import USE_CASE_WEIGHTS
from app.utils.scoring import (
    budget_score,
    cpu_score,
    gpu_score,
    ram_score,
    rating_score,
    storage_score,
    value_score,
)


class RankingService:
    """Score products against user intent with editable weighted components."""

    def rank(self, products: List[Product], interpreted: InterpretedRequest) -> List[Product]:
        """Return products sorted by descending score."""
        weights = USE_CASE_WEIGHTS.get(interpreted.use_case, USE_CASE_WEIGHTS["general"])

        ranked: List[Product] = []
        for product in products:
            component_scores = self._score_product(product, interpreted)
            total = self._weighted_total(component_scores, weights)
            product.score = round(total, 3)
            product.short_reason = self._build_short_reason(product, interpreted)
            ranked.append(product)

        ranked.sort(key=lambda p: p.score or 0.0, reverse=True)
        return ranked

    def _score_product(self, product: Product, interpreted: InterpretedRequest) -> Dict[str, float]:
        budget = budget_score(product.price, interpreted.budget_max)
        ram = ram_score(product.ram_gb)
        storage = storage_score(product.storage_gb)
        cpu = cpu_score(product.cpu)
        gpu = gpu_score(product.gpu)
        rating = rating_score(product.rating)
        quality = (ram + storage + cpu + gpu + rating) / 5.0
        value = value_score(product.price, quality)

        return {
            "budget": budget,
            "ram": ram,
            "storage": storage,
            "cpu": cpu,
            "gpu": gpu,
            "rating": rating,
            "value": value,
        }

    def _weighted_total(self, component_scores: Dict[str, float], weights: Dict[str, float]) -> float:
        total = 0.0
        for key, weight in weights.items():
            total += component_scores.get(key, 0.0) * weight
        return total

    def _build_short_reason(self, product: Product, interpreted: InterpretedRequest) -> str:
        reason_parts = []
        if interpreted.budget_max and product.price <= interpreted.budget_max:
            reason_parts.append("within budget")
        if product.ram_gb:
            reason_parts.append(f"{product.ram_gb}GB RAM")
        if product.cpu:
            reason_parts.append(product.cpu)
        if product.rating:
            reason_parts.append(f"{product.rating}/5 rating")
        return ", ".join(reason_parts[:4]) or "balanced specifications"

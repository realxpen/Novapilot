"""Transparent product ranking engine."""

import re
from typing import Dict, List

from app.config import get_settings
from app.schemas.product import Product
from app.schemas.response import InterpretedRequest
from app.services.ranking_weights import USE_CASE_WEIGHTS
from app.utils.currency import convert_amount
from app.utils.logger import get_logger
from app.utils.scoring import (
    budget_score,
    cpu_score,
    gpu_score,
    ram_score,
    rating_score,
    storage_score,
    value_score,
)


logger = get_logger(__name__)
settings = get_settings()


class RankingService:
    """Score products against user intent with editable weighted components."""

    def rank(self, products: List[Product], interpreted: InterpretedRequest) -> List[Product]:
        """Return products sorted by descending score."""
        weights = USE_CASE_WEIGHTS.get(interpreted.use_case, USE_CASE_WEIGHTS["general"])
        deduped_products = self._deduplicate_products(products)
        logger.info(
            "NOVAPILOT_DEBUG ranking_input count=%s deduped_count=%s use_case=%s weights=%s products=%s",
            len(products),
            len(deduped_products),
            interpreted.use_case,
            weights,
            [product.model_dump(mode="json") for product in deduped_products],
        )

        ranked: List[Product] = []
        for product in deduped_products:
            component_scores = self._score_product(product, interpreted)
            total = self._weighted_total(component_scores, weights)
            product.score = round(total, 3)
            product.short_reason = self._build_short_reason(product, interpreted)
            logger.info(
                "NOVAPILOT_DEBUG ranking_product name=%s component_scores=%s total=%s short_reason=%s",
                product.name,
                component_scores,
                product.score,
                product.short_reason,
            )
            ranked.append(product)

        ranked.sort(key=lambda p: p.score or 0.0, reverse=True)
        logger.info(
            "NOVAPILOT_DEBUG ranking_output count=%s ranked=%s",
            len(ranked),
            [product.model_dump(mode="json") for product in ranked],
        )
        return ranked

    def _score_product(self, product: Product, interpreted: InterpretedRequest) -> Dict[str, float]:
        comparable_price = self._price_in_budget_currency(product, interpreted)
        budget = budget_score(comparable_price, interpreted.budget_max)
        ram = ram_score(product.ram_gb)
        storage = storage_score(product.storage_gb)
        cpu = cpu_score(product.cpu)
        gpu = gpu_score(product.gpu)
        rating = rating_score(product.rating)
        quality = (ram + storage + cpu + gpu + rating) / 5.0
        value = value_score(comparable_price, quality)

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
        comparable_price = self._price_in_budget_currency(product, interpreted)
        if interpreted.budget_max and comparable_price <= interpreted.budget_max:
            reason_parts.append("within budget")
        if product.ram_gb:
            reason_parts.append(f"{product.ram_gb}GB RAM")
        if product.cpu:
            reason_parts.append(product.cpu)
        if product.rating:
            reason_parts.append(f"{product.rating}/5 rating")
        return ", ".join(reason_parts[:4]) or "balanced specifications"

    def _deduplicate_products(self, products: List[Product]) -> List[Product]:
        if len(products) <= 1:
            return list(products)

        kept: dict[str, Product] = {}
        for product in products:
            key = self._product_dedupe_key(product)
            existing = kept.get(key)
            if existing is None or self._is_better_variant(product, existing):
                kept[key] = product

        deduped = list(kept.values())
        if len(deduped) != len(products):
            logger.info(
                "NOVAPILOT_DEBUG ranking_dedup removed=%s before=%s after=%s",
                len(products) - len(deduped),
                len(products),
                len(deduped),
            )
        return deduped

    def _product_dedupe_key(self, product: Product) -> str:
        name = (product.name or "").lower()
        cleaned = re.sub(r"[^a-z0-9\s]", " ", name)
        color_stopwords = {
            "black",
            "blue",
            "navy",
            "white",
            "gray",
            "grey",
            "gold",
            "silver",
            "green",
            "red",
            "purple",
            "awesome",
            "midnight",
            "sunset",
            "iceblue",
            "ice",
            "lemon",
            "lilac",
        }
        tokens = [token for token in cleaned.split() if token not in color_stopwords]
        base_tokens = tokens[:12] if tokens else ["unknown"]
        base = " ".join(base_tokens)

        ram = product.ram_gb or self._extract_first_int(name, r"(\d{1,2})\s*gb")
        storage = product.storage_gb or self._extract_first_int(name, r"(\d{2,4})\s*gb")
        return f"{product.store}|{base}|ram:{ram or 0}|storage:{storage or 0}"

    def _extract_first_int(self, text: str, pattern: str) -> int | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _is_better_variant(self, candidate: Product, current: Product) -> bool:
        candidate_rating = candidate.rating if candidate.rating is not None else -1.0
        current_rating = current.rating if current.rating is not None else -1.0
        if candidate_rating != current_rating:
            return candidate_rating > current_rating
        return candidate.price < current.price

    def _price_in_budget_currency(self, product: Product, interpreted: InterpretedRequest) -> float:
        converted = convert_amount(
            product.price,
            product.currency,
            interpreted.budget_currency,
            settings.usd_to_ngn_rate,
        )
        return converted if converted is not None else product.price

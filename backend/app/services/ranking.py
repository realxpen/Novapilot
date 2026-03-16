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
FAMILY_STOPWORDS = {
    "android",
    "backlight",
    "battery",
    "black",
    "blue",
    "gold",
    "gray",
    "grey",
    "green",
    "keyboard",
    "laptop",
    "midnight",
    "navy",
    "phone",
    "pro",
    "red",
    "rom",
    "silver",
    "ssd",
    "stand",
    "storage",
    "tablet",
    "touchscreen",
    "ultra",
    "white",
    "windows",
}
FAMILY_SPEC_PATTERNS = (
    r"^\d{1,4}(gb|tb|mah|hz|mp)$",
    r"^\d+(?:\.\d+)?in$",
    r"^\d+(?:\.\d+)?$",
    r"^i[3579]$",
    r"^ryzen[3579]$",
    r"^snapdragon$",
    r"^dimensity$",
    r"^helio$",
    r"^core$",
    r"^intel$",
    r"^amd$",
    r"^gen\d+$",
    r"^\d+(st|nd|rd|th)$",
)


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

        # If family-based dedupe collapses the live shortlist below 3 items, fall back to a
        # looser URL/name-based uniqueness check so we keep enough real variants to compare.
        if len(deduped) < 3 and len(products) >= 3:
            url_unique: list[Product] = []
            seen_keys: set[str] = set()
            for product in products:
                key = (product.url or "").strip().lower()
                if not key:
                    key = f"{product.store.strip().lower()}::{product.name.strip().lower()}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                url_unique.append(product)

            if len(url_unique) > len(deduped):
                logger.info(
                    "NOVAPILOT_DEBUG ranking_dedup_fallback before=%s family_after=%s url_after=%s",
                    len(products),
                    len(deduped),
                    len(url_unique),
                )
                return url_unique
        return deduped

    def _product_dedupe_key(self, product: Product) -> str:
        name = (product.name or "").lower()
        cleaned = re.sub(r"[^a-z0-9\s]", " ", name)
        tokens = [token for token in cleaned.split() if token]
        family_tokens: list[str] = []
        for token in tokens:
            if token in FAMILY_STOPWORDS:
                continue
            if any(re.fullmatch(pattern, token, flags=re.IGNORECASE) for pattern in FAMILY_SPEC_PATTERNS):
                continue
            if token.endswith("gb") or token.endswith("tb"):
                continue
            family_tokens.append(token)

        # Alternatives should represent distinct product families, not nearby variants.
        family_key = " ".join(family_tokens[:6]) if family_tokens else "unknown"
        return f"{product.store}|{family_key}"

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

"""Extraction and normalization service for raw store product payloads."""

from typing import Any, Dict, List

from app.schemas.product import Product
from app.utils.normalizers import (
    extract_ram_gb,
    extract_screen_size,
    extract_storage_gb,
    normalize_currency,
    parse_price,
)


class ExtractionService:
    """Convert store-specific raw data into unified product objects."""

    def normalize_products(self, site: str, raw_products: List[Dict[str, Any]]) -> List[Product]:
        """Normalize products from one store with graceful field handling."""
        normalized: List[Product] = []
        for item in raw_products:
            if site in {"jumia", "konga", "slot", "jiji"}:
                normalized.append(self._normalize_marketplace(site, item))
            elif site == "amazon":
                normalized.append(self._normalize_amazon(item))
        return normalized

    def _normalize_marketplace(self, site: str, item: Dict[str, Any]) -> Product:
        specs = item.get("specs", "")
        return Product(
            name=item.get("title", "Unknown Product"),
            store=site,
            price=parse_price(item.get("price_text")),
            currency=normalize_currency(item.get("currency")),
            rating=parse_price(item.get("rating_text")),
            ram_gb=extract_ram_gb(specs),
            storage_gb=extract_storage_gb(specs),
            cpu=self._extract_cpu(specs),
            gpu=self._extract_gpu(specs),
            screen_size=extract_screen_size(specs),
            url=item.get("url"),
            image_url=item.get("image"),
        )

    def _normalize_amazon(self, item: Dict[str, Any]) -> Product:
        details = item.get("details", "")
        return Product(
            name=item.get("name", "Unknown Product"),
            store="amazon",
            price=parse_price(item.get("amount")),
            currency=normalize_currency(item.get("currency_code")),
            rating=float(item["rating"]) if item.get("rating") is not None else None,
            ram_gb=extract_ram_gb(details),
            storage_gb=extract_storage_gb(details),
            cpu=self._extract_cpu(details),
            gpu=self._extract_gpu(details),
            screen_size=extract_screen_size(details),
            url=item.get("product_url"),
            image_url=item.get("image_url"),
        )

    def _extract_cpu(self, text: str) -> str | None:
        lowered = text.lower()
        if "intel core i7" in lowered:
            return "Intel Core i7"
        if "intel core i5" in lowered:
            return "Intel Core i5"
        if "ryzen 7" in lowered:
            return "AMD Ryzen 7"
        if "apple m2" in lowered:
            return "Apple M2"
        return None

    def _extract_gpu(self, text: str) -> str | None:
        lowered = text.lower()
        if "rtx 3050" in lowered:
            return "NVIDIA RTX 3050"
        if "iris xe" in lowered:
            return "Intel Iris Xe"
        if "radeon" in lowered:
            return "AMD Radeon Graphics"
        if "integrated" in lowered:
            return "Integrated"
        return None

"""Extraction and normalization service for raw store product payloads."""

import re
from typing import Any, Dict, List
from urllib.parse import urljoin

from app.schemas.product import Product
from app.utils.logger import get_logger
from app.utils.normalizers import (
    extract_ram_gb,
    extract_screen_size,
    extract_storage_gb,
    normalize_currency,
    parse_price,
)


logger = get_logger(__name__)


class ExtractionService:
    """Convert store-specific raw data into unified product objects."""

    STORE_BASE_URLS = {
        "jumia": "https://www.jumia.com.ng",
        "konga": "https://www.konga.com",
        "slot": "https://slot.ng",
        "jiji": "https://jiji.ng",
        "amazon": "https://www.amazon.com",
    }

    def normalize_products(self, site: str, raw_products: List[Dict[str, Any]]) -> List[Product]:
        """Normalize products from one store with graceful field handling."""
        normalized: List[Product] = []
        for index, item in enumerate(raw_products):
            if site in {"jumia", "konga", "slot", "jiji"}:
                product = self._normalize_marketplace(site, item)
            elif site == "amazon":
                product = self._normalize_amazon(item)
            else:
                continue
            normalized.append(product)
            logger.info(
                "NOVAPILOT_DEBUG normalized_product site=%s index=%s raw=%s normalized=%s",
                site,
                index,
                item,
                product.model_dump(mode="json"),
            )
        return normalized

    def _normalize_marketplace(self, site: str, item: Dict[str, Any]) -> Product:
        title = item.get("title", "Unknown Product")
        specs = item.get("specs", "")
        text_blob = " ".join(str(part) for part in [title, specs] if part)
        rating_text = item.get("rating_text", item.get("rating"))
        product_url = self._normalize_url(site, item.get("url"))
        image_url = self._normalize_image_url(site, item.get("image"))
        return Product(
            name=title,
            store=site,
            price=parse_price(item.get("price_text")),
            currency=normalize_currency(item.get("currency")),
            rating=self._parse_rating_value(rating_text),
            ram_gb=extract_ram_gb(text_blob),
            storage_gb=extract_storage_gb(text_blob),
            cpu=self._extract_cpu(text_blob),
            gpu=self._extract_gpu(text_blob),
            screen_size=extract_screen_size(text_blob),
            url=product_url,
            image_url=image_url,
        )

    def _normalize_amazon(self, item: Dict[str, Any]) -> Product:
        details = item.get("details", "")
        product_url = self._normalize_url("amazon", item.get("product_url"))
        image_url = self._normalize_image_url("amazon", item.get("image_url"))
        return Product(
            name=item.get("name", "Unknown Product"),
            store="amazon",
            price=parse_price(item.get("amount")),
            currency=normalize_currency(item.get("currency_code")),
            rating=self._parse_rating_value(item.get("rating")),
            ram_gb=extract_ram_gb(details),
            storage_gb=extract_storage_gb(details),
            cpu=self._extract_cpu(details),
            gpu=self._extract_gpu(details),
            screen_size=extract_screen_size(details),
            url=product_url,
            image_url=image_url,
        )

    def _normalize_url(self, site: str, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        url = value.strip()
        if not url:
            return None

        if url.startswith("//"):
            return f"https:{url}"

        if url.startswith("http://") or url.startswith("https://"):
            return url

        base = self.STORE_BASE_URLS.get(site.lower())
        if not base:
            return None
        return urljoin(base, url)

    def _normalize_image_url(self, site: str, value: Any) -> str | None:
        url = self._normalize_url(site, value)
        if not url:
            return None
        lowered = url.lower()
        if lowered.startswith("data:"):
            return None
        if site.lower() == "jumia":
            if "jumia.com.ng" not in lowered and "jumia.is" not in lowered:
                return None
        return url

    def _extract_cpu(self, text: str) -> str | None:
        lowered = text.lower()
        if "intel core i7" in lowered:
            return "Intel Core i7"
        if "intel core i5" in lowered:
            return "Intel Core i5"
        if "intel core i3" in lowered:
            return "Intel Core i3"
        if "ryzen 7" in lowered:
            return "AMD Ryzen 7"
        if "ryzen 5" in lowered:
            return "AMD Ryzen 5"
        if "apple m2" in lowered:
            return "Apple M2"
        if "apple m1" in lowered:
            return "Apple M1"
        if "snapdragon" in lowered:
            match = re.search(r"(snapdragon\s*[a-z0-9\+\-\s]{1,24})", text, flags=re.IGNORECASE)
            return match.group(1).strip() if match else "Snapdragon"
        if "dimensity" in lowered:
            match = re.search(r"(dimensity\s*[a-z0-9\+\-\s]{1,24})", text, flags=re.IGNORECASE)
            return match.group(1).strip() if match else "Dimensity"
        if "exynos" in lowered:
            match = re.search(r"(exynos\s*[a-z0-9\+\-\s]{1,24})", text, flags=re.IGNORECASE)
            return match.group(1).strip() if match else "Exynos"
        if "helio" in lowered:
            match = re.search(r"(helio\s*[a-z0-9\+\-\s]{1,24})", text, flags=re.IGNORECASE)
            return match.group(1).strip() if match else "Helio"
        if "tensor" in lowered:
            match = re.search(r"(tensor\s*[a-z0-9\+\-\s]{1,24})", text, flags=re.IGNORECASE)
            return match.group(1).strip() if match else "Google Tensor"
        if "bionic" in lowered:
            match = re.search(r"(a\d{1,2}\s*bionic)", text, flags=re.IGNORECASE)
            return match.group(1).strip() if match else "Apple Bionic"
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

    def _parse_rating_value(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            numeric = float(value)
            return numeric if 0 <= numeric <= 5 else None

        text = str(value).strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered in {"none", "null", "n/a", "na", "not rated", "no rating"}:
            return None

        matches = re.findall(r"\d(?:\.\d+)?", text)
        if not matches:
            return None
        try:
            numeric = float(matches[0])
        except ValueError:
            return None
        return numeric if 0 <= numeric <= 5 else None

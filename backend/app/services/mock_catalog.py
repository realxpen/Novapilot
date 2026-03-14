"""Deterministic mock product data for local fallback mode."""

from __future__ import annotations

from typing import Any

from app.schemas.response import InterpretedRequest


class MockCatalogService:
    """Build deterministic mock store payloads when live automation fails."""

    def build_store_products(
        self,
        site: str,
        interpreted: InterpretedRequest,
        query: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        category = interpreted.category.lower()
        lowered_query = query.lower()
        currency = interpreted.budget_currency.upper() if interpreted.budget_currency else "NGN"

        if "powerbank" in lowered_query or "power bank" in lowered_query:
            items = [
                self._item("Anker PowerCore 20000", 78000, currency, 4.7, "20000mAh; USB-C; fast charging"),
                self._item("Oraimo Traveler 3 27000", 65000, currency, 4.4, "27000mAh; dual USB-A; LED display"),
                self._item("Xiaomi Redmi Power Bank 20000", 59000, currency, 4.5, "20000mAh; USB-C; slim body"),
            ]
        elif category == "smartphone":
            items = [
                self._item("Samsung Galaxy A35 5G 8GB 256GB", 465000, currency, 4.5, "8GB RAM; 256GB storage; 6.6 inch AMOLED"),
                self._item("Redmi Note 13 Pro 8GB 256GB", 429000, currency, 4.4, "8GB RAM; 256GB storage; 200MP camera"),
                self._item("Tecno Camon 30 8GB 256GB", 389000, currency, 4.3, "8GB RAM; 256GB storage; 5000mAh battery"),
            ]
        elif category == "laptop":
            items = [
                self._item("Dell Latitude 7490 16GB 512GB", 845000, currency, 4.4, "Intel Core i5; 16GB RAM; 512GB SSD"),
                self._item("HP EliteBook 840 G6 16GB 512GB", 825000, currency, 4.3, "Intel Core i5; 16GB RAM; 512GB SSD"),
                self._item("Lenovo IdeaPad 3 Core i5 16GB 512GB", 785000, currency, 4.2, "Intel Core i5; 16GB RAM; 512GB SSD"),
            ]
        elif category == "tablet":
            items = [
                self._item("Samsung Galaxy Tab S9 FE 8GB 256GB", 690000, currency, 4.5, "8GB RAM; 256GB storage; S Pen"),
                self._item("Xiaomi Pad 6 8GB 256GB", 575000, currency, 4.4, "8GB RAM; 256GB storage; 11 inch display"),
                self._item("iPad Air 5 256GB", 895000, currency, 4.7, "256GB storage; 10.9 inch display; Apple Pencil support"),
            ]
        elif category == "audio":
            items = [
                self._item("Sony WH-CH720N", 185000, currency, 4.6, "Noise cancelling; long battery life"),
                self._item("Soundcore Space One", 159000, currency, 4.5, "ANC; USB-C; strong app support"),
                self._item("JBL Tune 770NC", 139000, currency, 4.4, "ANC; multipoint; 70h battery"),
            ]
        else:
            items = [
                self._item("NovaPilot Mock Item A", 120000, currency, 4.3, "Representative mock data"),
                self._item("NovaPilot Mock Item B", 98000, currency, 4.1, "Representative mock data"),
                self._item("NovaPilot Mock Item C", 86000, currency, 4.0, "Representative mock data"),
            ]

        budget = interpreted.budget_max
        if budget is not None:
            budget_filtered = [item for item in items if item["price"] <= budget]
            if budget_filtered:
                items = budget_filtered

        return [self._to_store_shape(site, item) for item in items[: max(1, limit)]]

    def _item(
        self,
        name: str,
        price: float,
        currency: str,
        rating: float,
        specs: str,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "price": price,
            "currency": currency,
            "rating": rating,
            "specs": specs,
        }

    def _format_price_text(self, price: float, currency: str) -> str:
        if currency.upper() == "USD":
            return f"${price:,.2f}"
        return f"₦{int(price):,}"

    def _to_store_shape(self, site: str, item: dict[str, Any]) -> dict[str, Any]:
        price_text = self._format_price_text(item["price"], item["currency"])
        if site.lower() == "amazon":
            return {
                "name": item["name"],
                "amount": item["price"],
                "currency_code": item["currency"],
                "rating": item["rating"],
                "details": item["specs"],
                "product_url": None,
                "image_url": None,
            }
        return {
            "title": item["name"],
            "price_text": price_text,
            "currency": item["currency"],
            "rating_text": str(item["rating"]),
            "specs": item["specs"],
            "url": None,
            "image": None,
        }

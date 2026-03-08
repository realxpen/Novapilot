"""AWS-ready placeholder client for Nova Act store automation workflows."""

from typing import Any, Dict, List

from app.clients.interfaces import StoreAutomationClient


class NovaActClient(StoreAutomationClient):
    """Placeholder Nova Act client that returns mock raw store results.

    This adapter keeps the expected client shape while avoiding real browser/network calls.
    """

    def run_store_workflow(
        self,
        site: str,
        interpreted_request: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Run placeholder store workflow and return mock raw product dictionaries.

        TODO(AWS-NOVAACT-AUTOMATION):
        - Select workflow by `site` (e.g., search_jumia_laptops, search_amazon_laptops).
        - Pass `interpreted_request` as structured workflow input.
        - Trigger Nova Act browser workflow and collect extracted result payload.
        """
        site_key = site.lower()
        if site_key == "jumia":
            return self._mock_jumia_raw()
        if site_key == "amazon":
            return self._mock_amazon_raw()
        return []

    def _mock_jumia_raw(self) -> List[Dict[str, Any]]:
        return [
            {
                "title": "Lenovo ThinkPad E14 - 16GB RAM 512GB SSD Core i7",
                "price_text": "NGN 785,000",
                "currency": "NGN",
                "rating_text": "4.4",
                "specs": "16GB RAM, 512GB SSD, Intel Core i7, 14 inch, Intel Iris Xe",
                "url": "https://www.jumia.com.ng/lenovo-thinkpad-e14",
                "image": "https://images.jumia.com.ng/lenovo-thinkpad-e14.jpg",
            },
            {
                "title": "HP 250 G8 - 8GB RAM 256GB SSD Core i3",
                "price_text": "NGN 455,000",
                "currency": "NGN",
                "rating_text": "3.9",
                "specs": "8GB RAM, 256GB SSD, Intel Core i3, 15.6 inch",
                "url": "https://www.jumia.com.ng/hp-250-g8",
                "image": "https://images.jumia.com.ng/hp-250-g8.jpg",
            },
        ]

    def _mock_amazon_raw(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Acer Swift Go 14 - 16GB RAM 512GB SSD Core i7",
                "amount": "NGN 805,000",
                "currency_code": "NGN",
                "rating": 4.5,
                "details": "16GB RAM, 512GB SSD, Intel Core i7, 14 inch, Intel Iris Xe",
                "product_url": "https://www.amazon.com/acer-swift-go-14",
                "image_url": "https://m.media-amazon.com/images/acer-swift-go-14.jpg",
            },
            {
                "name": "Budget Laptop 15 - 4GB RAM 128GB SSD Celeron",
                "amount": "NGN 335,000",
                "currency_code": "NGN",
                "rating": 3.5,
                "details": "4GB RAM, 128GB SSD, Intel Celeron, 15.6 inch, Integrated GPU",
                "product_url": "https://www.amazon.com/budget-laptop-15",
                "image_url": "https://m.media-amazon.com/images/budget-laptop-15.jpg",
            },
        ]

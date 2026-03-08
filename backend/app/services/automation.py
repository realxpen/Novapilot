"""Automation layer with mock store search data.

This service is intentionally structured as a replaceable abstraction.
Later, its methods can delegate to a real Nova Act workflow client.
"""

from typing import Any, Dict, List

from app.clients.nova_act_client import NovaActClient
from app.clients.interfaces import StoreAutomationClient
from app.schemas.response import InterpretedRequest
from app.utils.logger import get_logger


logger = get_logger(__name__)


class AutomationService:
    """Run store-level search/collection workflows."""

    def __init__(
        self,
        nova_act_client: StoreAutomationClient | None = None,
        use_nova_act: bool = False,
    ) -> None:
        self.nova_act_client = nova_act_client or NovaActClient()
        self.use_nova_act = use_nova_act

    def run_site_workflow(self, site: str, interpreted: InterpretedRequest) -> List[Dict[str, Any]]:
        """Execute automation for one store and return raw product dictionaries."""
        if self.use_nova_act:
            try:
                return self.nova_act_client.run_store_workflow(
                    site=site,
                    interpreted_request=interpreted.model_dump(),
                )
            except NotImplementedError:
                logger.info("Nova Act provider not implemented yet. Falling back to mock data.")

        site_key = site.lower()
        if site_key == "jumia":
            return self._mock_jumia_products(interpreted)
        if site_key == "amazon":
            return self._mock_amazon_products(interpreted)
        raise ValueError(f"Unsupported site '{site}'")

    def _mock_jumia_products(self, interpreted: InterpretedRequest) -> List[Dict[str, Any]]:
        """Jumia mock catalog: mixed quality options across budget ranges."""
        return [
            {
                "title": "HP Pavilion 15 - 16GB RAM 512GB SSD Core i7",
                "price_text": "NGN 760,000",
                "currency": "NGN",
                "rating_text": "4.4",
                "specs": "16GB RAM, 512GB SSD, Intel Core i7, 15.6 inch FHD, Intel Iris Xe",
                "url": "https://www.jumia.com.ng/hp-pavilion-15",
                "image": "https://images.jumia.com.ng/hp-pavilion-15.jpg",
            },
            {
                "title": "Lenovo IdeaPad Slim 3 - 8GB RAM 512GB SSD Core i5",
                "price_text": "NGN 590,000",
                "currency": "NGN",
                "rating_text": "4.2",
                "specs": "8GB RAM, 512GB SSD, Intel Core i5, 15.6 inch",
                "url": "https://www.jumia.com.ng/lenovo-ideapad-slim-3",
                "image": "https://images.jumia.com.ng/lenovo-slim3.jpg",
            },
            {
                "title": "Dell Inspiron 14 - 16GB RAM 1TB SSD Ryzen 7",
                "price_text": "NGN 820,000",
                "currency": "NGN",
                "rating_text": "4.6",
                "specs": "16GB RAM, 1TB SSD, AMD Ryzen 7, 14 inch, Radeon Graphics",
                "url": "https://www.jumia.com.ng/dell-inspiron-14",
                "image": "https://images.jumia.com.ng/dell-inspiron-14.jpg",
            },
            {
                "title": "ASUS VivoBook 15 - 16GB RAM 512GB SSD Core i5",
                "price_text": "NGN 690,000",
                "currency": "NGN",
                "rating_text": "4.3",
                "specs": "16GB RAM, 512GB SSD, Intel Core i5, 15.6 inch, Intel UHD",
                "url": "https://www.jumia.com.ng/asus-vivobook-15",
                "image": "https://images.jumia.com.ng/asus-vivobook-15.jpg",
            },
            {
                "title": "Acer Aspire 3 - 4GB RAM 128GB SSD Core i3",
                "price_text": "NGN 365,000",
                "currency": "NGN",
                "rating_text": "3.7",
                "specs": "4GB RAM, 128GB SSD, Intel Core i3, 15.6 inch, Intel UHD",
                "url": "https://www.jumia.com.ng/acer-aspire-3",
                "image": "https://images.jumia.com.ng/acer-aspire-3.jpg",
            },
            {
                "title": "Dell Vostro 3520 - 8GB RAM 1TB HDD Core i5",
                "price_text": "NGN 515,000",
                "currency": "NGN",
                "rating_text": "3.9",
                "specs": "8GB RAM, 1TB HDD, Intel Core i5, 15.6 inch",
                "url": "https://www.jumia.com.ng/dell-vostro-3520",
                "image": "https://images.jumia.com.ng/dell-vostro-3520.jpg",
            },
        ]

    def _mock_amazon_products(self, interpreted: InterpretedRequest) -> List[Dict[str, Any]]:
        """Amazon mock catalog: includes high-end, balanced, and weak options."""
        return [
            {
                "name": "Acer Swift X 14 - 16GB RAM 512GB SSD Ryzen 7 RTX 3050",
                "amount": "NGN 799,999",
                "currency_code": "NGN",
                "rating": 4.5,
                "details": "16GB RAM, 512GB SSD, AMD Ryzen 7, NVIDIA RTX 3050, 14 inch",
                "product_url": "https://www.amazon.com/acer-swift-x-14",
                "image_url": "https://m.media-amazon.com/images/acer-swift-x.jpg",
            },
            {
                "name": "Apple MacBook Air M2 - 8GB RAM 256GB SSD",
                "amount": "NGN 850,000",
                "currency_code": "NGN",
                "rating": 4.7,
                "details": "8GB RAM, 256GB SSD, Apple M2, 13.6 inch, Integrated GPU",
                "product_url": "https://www.amazon.com/macbook-air-m2",
                "image_url": "https://m.media-amazon.com/images/macbook-air-m2.jpg",
            },
            {
                "name": "MSI Modern 15 - 16GB RAM 512GB SSD Core i7",
                "amount": "NGN 775,000",
                "currency_code": "NGN",
                "rating": 4.3,
                "details": "16GB RAM, 512GB SSD, Intel Core i7, 15.6 inch, Iris Xe",
                "product_url": "https://www.amazon.com/msi-modern-15",
                "image_url": "https://m.media-amazon.com/images/msi-modern-15.jpg",
            },
            {
                "name": "Samsung Galaxy Book3 - 16GB RAM 512GB SSD Core i5",
                "amount": "NGN 735,000",
                "currency_code": "NGN",
                "rating": 4.4,
                "details": "16GB RAM, 512GB SSD, Intel Core i5, 15.6 inch AMOLED",
                "product_url": "https://www.amazon.com/galaxy-book3",
                "image_url": "https://m.media-amazon.com/images/galaxy-book3.jpg",
            },
            {
                "name": "ASUS TUF Gaming A15 - 16GB RAM 512GB SSD Ryzen 7 RTX 4060",
                "amount": "NGN 980,000",
                "currency_code": "NGN",
                "rating": 4.6,
                "details": "16GB RAM, 512GB SSD, AMD Ryzen 7, NVIDIA RTX 4060, 15.6 inch",
                "product_url": "https://www.amazon.com/asus-tuf-a15",
                "image_url": "https://m.media-amazon.com/images/asus-tuf-a15.jpg",
            },
            {
                "name": "HP 14s - 8GB RAM 256GB SSD Core i3",
                "amount": "NGN 470,000",
                "currency_code": "NGN",
                "rating": 4.0,
                "details": "8GB RAM, 256GB SSD, Intel Core i3, 14 inch, Integrated GPU",
                "product_url": "https://www.amazon.com/hp-14s",
                "image_url": "https://m.media-amazon.com/images/hp-14s.jpg",
            },
            {
                "name": "Chuwi HeroBook Pro - 8GB RAM 256GB SSD Celeron",
                "amount": "NGN 420,000",
                "currency_code": "NGN",
                "rating": 3.6,
                "details": "8GB RAM, 256GB SSD, Intel Celeron, 14.1 inch, Integrated GPU",
                "product_url": "https://www.amazon.com/chuwi-herobook-pro",
                "image_url": "https://m.media-amazon.com/images/chuwi-herobook.jpg",
            },
            {
                "name": "Razer Blade 15 - 32GB RAM 1TB SSD Core i9 RTX 4070",
                "amount": "NGN 1,450,000",
                "currency_code": "NGN",
                "rating": 4.8,
                "details": "32GB RAM, 1TB SSD, Intel Core i9, NVIDIA RTX 4070, 15.6 inch",
                "product_url": "https://www.amazon.com/razer-blade-15",
                "image_url": "https://m.media-amazon.com/images/razer-blade-15.jpg",
            },
            {
                "name": "Refurbished Ultrabook 13 - 8GB RAM 256GB SSD Core i5",
                "amount": "NGN 540,000",
                "currency_code": "NGN",
                "rating": None,
                "details": "8GB RAM, 256GB SSD, Intel Core i5, 13.3 inch, Integrated GPU",
                "product_url": "https://www.amazon.com/refurb-ultrabook-13",
                "image_url": "https://m.media-amazon.com/images/refurb-ultrabook-13.jpg",
            },
        ]

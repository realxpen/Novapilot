"""Automation layer backed by live Nova Act workflows only."""

from dataclasses import dataclass
import re
from typing import Any, Dict, List

from app.clients.interfaces import StoreAutomationClient
from app.clients.nova_act_client import NovaActClient
from app.schemas.response import InterpretedRequest
from app.utils.currency import convert_amount, site_budget_currency
from app.utils.logger import get_logger
from app.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


@dataclass
class StoreWorkflowResult:
    """Structured result for one store automation run."""

    site: str
    raw_products: List[Dict[str, Any]]
    source: str
    warning_message: str | None = None
    live_error_message: str | None = None


class AutomationService:
    """Run live store-level workflows and return extracted product payloads."""

    QUERY_STOPWORDS = {
        "best",
        "top",
        "good",
        "great",
        "cheap",
        "budget",
        "under",
        "below",
        "less",
        "than",
        "around",
        "about",
        "for",
        "with",
        "without",
        "find",
        "need",
        "want",
        "looking",
        "searching",
        "buy",
        "get",
        "me",
        "my",
        "the",
        "a",
        "an",
        "in",
        "on",
        "to",
    }

    def __init__(
        self,
        nova_act_client: StoreAutomationClient | None = None,
        use_nova_act: bool = True,
        strict_live_mode: bool = True,
    ) -> None:
        self.nova_act_client = nova_act_client or NovaActClient()
        self.use_nova_act = use_nova_act
        self.strict_live_mode = strict_live_mode

    def run_site_workflow(
        self,
        site: str,
        interpreted: InterpretedRequest,
        query: str,
        user_location: str | None = None,
    ) -> StoreWorkflowResult:
        """Execute a live workflow for one store and return raw product dictionaries."""
        if not self.use_nova_act:
            raise RuntimeError("Live Nova Act automation is disabled for this backend.")

        payload: Dict[str, Any] = interpreted.model_dump()
        payload["query"] = query
        if user_location:
            payload["user_location"] = user_location
        payload["search_terms"] = self._build_search_terms(interpreted, query, site)
        site_key = site.strip().lower()
        if site_key == "jumia":
            category_key = interpreted.category.lower()
            if category_key == "smartphone":
                payload["max_results"] = max(5, int(interpreted.top_n or 5))
                payload["max_search_terms"] = 5
            elif category_key == "laptop":
                payload["max_results"] = max(5, int(interpreted.top_n or 5))
                payload["max_search_terms"] = 5
            elif category_key == "tablet":
                payload["max_results"] = max(5, int(interpreted.top_n or 5))
                payload["max_search_terms"] = 5
            else:
                payload["max_results"] = max(4, min(int(interpreted.top_n or 4), 5))
                payload["max_search_terms"] = 4
        elif site_key == "amazon":
            payload["max_results"] = max(5, int(interpreted.top_n or 5))
            payload["max_search_terms"] = 4
        elif site_key == "shopinverse":
            payload["max_results"] = max(5, int(interpreted.top_n or 5))
            payload["max_search_terms"] = 4
        else:
            payload["max_results"] = max(4, min(int(interpreted.top_n or 4), 5))
            payload["max_search_terms"] = 3
        target_budget_currency = site_budget_currency(site)
        converted_budget_max = convert_amount(
            interpreted.budget_max,
            interpreted.budget_currency,
            target_budget_currency,
            settings.usd_to_ngn_rate,
        )
        payload["budget_currency"] = target_budget_currency
        payload["budget_max"] = converted_budget_max if converted_budget_max is not None else interpreted.budget_max
        payload["original_budget_currency"] = interpreted.budget_currency
        payload["original_budget_max"] = interpreted.budget_max
        logger.info(
            "NOVAPILOT_DEBUG automation_mode site=%s mode=%s strict_live_mode=%s payload=%s",
            site,
            "live_nova_act" if self.use_nova_act else "live_disabled",
            self.strict_live_mode,
            payload,
        )
        logger.info(
            "NOVAPILOT_DEBUG automation_budget_conversion site=%s original_budget_currency=%s original_budget_max=%s target_budget_currency=%s converted_budget_max=%s usd_to_ngn_rate=%s",
            site,
            interpreted.budget_currency,
            interpreted.budget_max,
            target_budget_currency,
            converted_budget_max,
            settings.usd_to_ngn_rate,
        )

        try:
            results = self.nova_act_client.run_store_workflow(
                site=site,
                interpreted_request=payload,
            )
            logger.info(
                "NOVAPILOT_DEBUG automation_result site=%s result_count=%s results=%s",
                site,
                len(results),
                results,
            )
            return StoreWorkflowResult(
                site=site,
                raw_products=results,
                source="live",
            )
        except Exception as exc:  # noqa: BLE001 - live errors must surface directly now
            logger.exception("NOVAPILOT_DEBUG automation_failed site=%s", site)
            raise RuntimeError(f"Nova Act live workflow failed for {site}: {exc}") from exc

    def _build_search_terms(
        self,
        interpreted: InterpretedRequest,
        query: str,
        site: str | None = None,
    ) -> List[str]:
        lowered_query = query.lower()
        site_key = (site or "").strip().lower()
        if "powerbank" in lowered_query or "power bank" in lowered_query:
            terms = [
                "Anker power bank 20000mAh",
                "Oraimo power bank 20000mAh",
                "Xiaomi power bank 20000mAh",
                "Samsung power bank 10000mAh",
                "power bank fast charging 20000mAh",
            ]
            return self._finalize_search_terms(site_key, query, terms)

        category = interpreted.category.lower()
        use_case = interpreted.use_case.lower()

        if category == "laptop" and use_case == "programming":
            if site_key == "jumia":
                terms = [
                    "Dell Latitude 7490 16GB 512GB laptop",
                    "HP EliteBook 840 G6 16GB 512GB laptop",
                    "Lenovo IdeaPad 3 Core i5 16GB 512GB laptop",
                    "Dell Inspiron 15 Core i5 16GB 512GB laptop",
                    "HP ProBook 450 G7 16GB 512GB laptop",
                    "laptop 16GB 512GB Core i5",
                ]
            else:
                terms = [
                    "ThinkPad T480 16GB 512GB laptop",
                    "ThinkPad T490 16GB 512GB laptop",
                    "HP EliteBook 840 G6 16GB 512GB laptop",
                    "HP EliteBook 840 G7 16GB 512GB laptop",
                    "Dell Latitude 7400 16GB 512GB laptop",
                    "Dell Latitude 7490 16GB 512GB laptop",
                    "laptop 16GB 512GB Core i5",
                ]
            return self._finalize_search_terms(site_key, query, terms)

        if category == "laptop" and use_case == "ui/ux design":
            terms = [
                "HP Envy x360 16GB 512GB laptop",
                "Dell Inspiron 14 16GB 512GB laptop",
                "Lenovo IdeaPad 5 16GB 512GB laptop",
                "laptop 16GB 512GB Ryzen 5",
            ]
            return self._finalize_search_terms(site_key, query, terms)

        if category == "smartphone":
            terms = [
                "Samsung Galaxy A55 8GB 256GB phone",
                "Samsung Galaxy A35 8GB 256GB phone",
                "Redmi Note 13 Pro 8GB 256GB phone",
                "Google Pixel 7a phone",
                "Infinix Zero 30 8GB 256GB phone",
                "Tecno Camon 30 phone",
                "phone 8GB 256GB",
            ]
            return self._finalize_search_terms(site_key, query, terms)

        if category == "tablet" and use_case == "ui/ux design":
            terms = [
                "Apple iPad Air 5 256GB tablet",
                "Apple iPad Pro 11 128GB tablet",
                "Samsung Galaxy Tab S9 FE 8GB 256GB tablet",
                "Samsung Galaxy Tab S8 8GB 128GB tablet",
                "Xiaomi Pad 6 8GB 256GB tablet",
                "Redmi Pad Pro 8GB 256GB tablet",
            ]
            return self._finalize_search_terms(site_key, query, terms)

        if category == "tablet":
            terms = [
                "Samsung Galaxy Tab S9 FE 8GB 256GB tablet",
                "Samsung Galaxy Tab S8 8GB 128GB tablet",
                "Xiaomi Pad 6 8GB 256GB tablet",
                "Redmi Pad Pro 8GB 256GB tablet",
                "Apple iPad Air 5 256GB tablet",
                "tablet 8GB 128GB standalone tablet",
            ]
            return self._finalize_search_terms(site_key, query, terms)

        if category == "audio":
            terms = [
                "Sony WH-CH720N headphones",
                "Soundcore Space One headphones",
                "JBL Tune 770NC headphones",
                "noise cancelling headphones",
            ]
            return self._finalize_search_terms(site_key, query, terms)

        return self._finalize_search_terms(
            site_key,
            query,
            self._build_generic_search_terms(interpreted, query),
        )

    def _finalize_search_terms(self, site_key: str, query: str, terms: List[str]) -> List[str]:
        normalized_query = " ".join(query.strip().split())
        if site_key not in {"amazon", "shopinverse"}:
            return self._dedupe_terms(terms)

        # Amazon and ShopInverse often respond better to the broad natural-language
        # intent first, then to concrete fallback model searches if needed.
        searchable_query = re.sub(r"\s+", " ", re.sub(r"[^\w\s/+.,-]", " ", normalized_query)).strip()
        return self._dedupe_terms([normalized_query, searchable_query, *terms])

    def _build_generic_search_terms(self, interpreted: InterpretedRequest, query: str) -> List[str]:
        category_keyword = {
            "laptop": "laptop",
            "tablet": "tablet",
            "smartphone": "phone",
            "audio": "headphones",
            "electronics": "electronics",
        }.get(interpreted.category.lower(), interpreted.category.lower())
        spec_hint = {
            "laptop": "16GB 512GB",
            "tablet": "8GB 256GB stylus",
            "smartphone": "8GB 256GB",
            "audio": "noise cancelling",
        }.get(interpreted.category.lower(), "")

        cleaned_query = self._simplify_query(query)
        terms: List[str] = []

        if cleaned_query:
            terms.append(cleaned_query)
            if category_keyword and category_keyword not in cleaned_query.lower():
                terms.append(f"{cleaned_query} {category_keyword}".strip())

        if category_keyword:
            use_case_fragment = self._simplify_query(interpreted.use_case)
            if use_case_fragment and use_case_fragment != "general":
                terms.append(f"{use_case_fragment} {category_keyword}".strip())
            if spec_hint:
                terms.append(f"{category_keyword} {spec_hint}".strip())
            terms.append(category_keyword)

        terms.append(query.strip())
        return self._dedupe_terms(terms)

    def _simplify_query(self, query: str) -> str:
        normalized = re.sub(r"[^\w\s/+.-]", " ", query.lower())
        tokens = normalized.split()
        kept: List[str] = []

        for token in tokens:
            if token in self.QUERY_STOPWORDS:
                continue
            if token in {"ngn", "naira", "usd", "dollar", "dollars"}:
                continue
            if token.isdigit():
                continue
            if re.fullmatch(r"\d+[kK]", token):
                continue
            kept.append(token)

        simplified = " ".join(kept).strip()
        return re.sub(r"\s+", " ", simplified)

    def _dedupe_terms(self, terms: List[str]) -> List[str]:
        seen: set[str] = set()
        ordered: List[str] = []
        for term in terms:
            normalized = re.sub(r"\s+", " ", term.strip().lower())
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(term.strip())
        return ordered

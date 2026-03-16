"""Site recommendation service with optional Bedrock-backed selection."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.clients.interfaces import SiteRecommendationClient
from app.schemas.response import InterpretedRequest


class SiteRecommendationService:
    """Recommend shopping sites from request context with model and rule fallbacks."""

    NIGERIA_PRIORITY = ["jumia", "konga", "slot", "jiji"]

    def __init__(self, recommendation_client: Optional[SiteRecommendationClient] = None) -> None:
        self.recommendation_client = recommendation_client

    def recommend(
        self,
        query: str,
        interpreted: InterpretedRequest,
        allowed_sites: List[str],
        user_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a selected site list plus metadata about the decision."""
        normalized_allowed = self._dedupe_sites(allowed_sites)
        if not normalized_allowed:
            return {
                "sites": [],
                "source": "fallback",
                "confidence": 0.0,
                "rationale": "No allowed sites were available for recommendation.",
            }

        model_result = self._try_client_recommendation(
            query=query,
            interpreted=interpreted,
            user_location=user_location,
            allowed_sites=normalized_allowed,
        )
        if model_result:
            return model_result

        return self._fallback_recommendation(
            interpreted=interpreted,
            allowed_sites=normalized_allowed,
            user_location=user_location,
        )

    def _try_client_recommendation(
        self,
        query: str,
        interpreted: InterpretedRequest,
        user_location: Optional[str],
        allowed_sites: List[str],
    ) -> Optional[Dict[str, Any]]:
        if not self.recommendation_client:
            return None

        payload = self.recommendation_client.recommend_sites(
            query=query,
            user_location=user_location,
            category=interpreted.category,
            budget_currency=interpreted.budget_currency,
            budget_max=interpreted.budget_max,
            allowed_sites=allowed_sites,
        )
        if not payload:
            return None

        recommended = self._filter_allowed_sites(payload.get("recommended_sites"), allowed_sites)
        if not recommended:
            return None

        confidence = payload.get("confidence")
        try:
            normalized_confidence = float(confidence) if confidence is not None else 0.7
        except (TypeError, ValueError):
            normalized_confidence = 0.7

        return {
            "sites": recommended,
            "source": "model",
            "confidence": max(0.0, min(normalized_confidence, 1.0)),
            "rationale": str(payload.get("rationale", "")).strip() or "Model selected the most relevant stores.",
            "excluded_sites": self._filter_allowed_sites(payload.get("excluded_sites"), allowed_sites),
        }

    def _fallback_recommendation(
        self,
        interpreted: InterpretedRequest,
        allowed_sites: List[str],
        user_location: Optional[str],
    ) -> Dict[str, Any]:
        is_nigeria = self._is_nigeria_market(user_location, interpreted.budget_currency)
        category = interpreted.category.lower()
        budget_max = interpreted.budget_max or 0

        recommended: List[str] = []
        if is_nigeria:
            recommended.extend(site for site in self.NIGERIA_PRIORITY if site in allowed_sites)
            rationale = "Nigeria fallback prioritized Jumia first for local device availability."
        else:
            recommended.extend(site for site in ["jumia", "konga", "slot", "jiji", "amazon"] if site in allowed_sites)
            rationale = "Fallback ranked broadly available marketplaces by expected category and availability fit."

        trimmed = self._trim_recommendations(self._dedupe_sites(recommended))
        if not trimmed:
            trimmed = self._trim_recommendations(allowed_sites)

        return {
            "sites": trimmed,
            "source": "fallback",
            "confidence": 0.55,
            "rationale": rationale,
        }

    def _is_nigeria_market(self, user_location: Optional[str], budget_currency: str) -> bool:
        location = (user_location or "").lower()
        return "nigeria" in location or budget_currency.upper() == "NGN"

    def _filter_allowed_sites(self, sites: Any, allowed_sites: List[str]) -> List[str]:
        if not isinstance(sites, list):
            return []
        allowed = set(allowed_sites)
        return [site for site in self._dedupe_sites([str(site).strip().lower() for site in sites]) if site in allowed]

    def _trim_recommendations(self, sites: List[str]) -> List[str]:
        return sites[:4] if len(sites) > 4 else sites

    def _dedupe_sites(self, sites: List[str]) -> List[str]:
        seen: set[str] = set()
        ordered: List[str] = []
        for site in sites:
            clean = site.strip().lower()
            if clean and clean not in seen:
                seen.add(clean)
                ordered.append(clean)
        return ordered

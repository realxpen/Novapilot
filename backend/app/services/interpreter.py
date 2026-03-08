"""Rule-based interpreter with optional model-provider override."""

import re
from typing import Dict, List, Optional

from app.clients.interfaces import InterpretationClient
from app.schemas.response import InterpretedRequest


class InterpreterService:
    """Interpret natural-language shopping prompts into structured constraints."""

    USE_CASE_PRIORITIES: Dict[str, List[str]] = {
        "ui/ux design": ["RAM", "CPU", "storage", "display", "portability"],
        "programming": ["RAM", "CPU", "storage"],
        "gaming": ["GPU", "RAM", "CPU", "display"],
        "general": ["price", "rating", "RAM"],
    }

    def __init__(self, interpretation_client: Optional[InterpretationClient] = None) -> None:
        self.interpretation_client = interpretation_client

    def interpret(self, query: str, top_n: int) -> InterpretedRequest:
        """Parse user query into an `InterpretedRequest`.

        If an interpretation client is configured, this first attempts provider-based
        interpretation, then falls back to deterministic rules.
        """
        interpreted = self._try_client_interpret(query, top_n)
        if interpreted:
            return interpreted

        category = self._detect_category(query)
        budget_currency, budget_max = self._detect_budget(query)
        use_case = self._detect_use_case(query)
        priorities = self.USE_CASE_PRIORITIES.get(use_case, self.USE_CASE_PRIORITIES["general"])

        return InterpretedRequest(
            category=category,
            budget_currency=budget_currency,
            budget_max=budget_max,
            use_case=use_case,
            priority_specs=priorities,
            top_n=top_n,
        )

    def _try_client_interpret(self, query: str, top_n: int) -> Optional[InterpretedRequest]:
        if not self.interpretation_client:
            return None
        payload = self.interpretation_client.interpret_query(query=query, top_n=top_n)
        if not payload:
            return None
        return InterpretedRequest(
            category=payload.get("category", self._detect_category(query)),
            budget_currency=payload.get("budget_currency", "NGN"),
            budget_max=payload.get("budget_max"),
            use_case=payload.get("use_case", self._detect_use_case(query)),
            priority_specs=payload.get("priority_specs", []),
            top_n=int(payload.get("top_n", top_n)),
        )

    def _detect_category(self, query: str) -> str:
        lowered = query.lower()
        if "laptop" in lowered:
            return "laptop"
        if "phone" in lowered or "smartphone" in lowered:
            return "smartphone"
        if "headphone" in lowered or "earbud" in lowered:
            return "audio"
        return "electronics"

    def _detect_budget(self, query: str) -> tuple[str, Optional[float]]:
        lowered = query.lower()
        currency = "NGN" if "\u20A6" in query or "ngn" in lowered or "naira" in lowered else "USD"
        patterns = [
            r"(?:under|below|less than)\s*(?:\u20A6|\$)?\s*([\d,]+(?:\.\d+)?)",
            r"(?:\u20A6|\$)\s*([\d,]+(?:\.\d+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, flags=re.IGNORECASE)
            if match:
                numeric = match.group(1).replace(",", "")
                try:
                    return currency, float(numeric)
                except ValueError:
                    continue
        return currency, None

    def _detect_use_case(self, query: str) -> str:
        lowered = query.lower()
        if "ui/ux" in lowered or "design" in lowered:
            return "ui/ux design"
        if "programming" in lowered or "coding" in lowered or "developer" in lowered:
            return "programming"
        if "gaming" in lowered or "game" in lowered:
            return "gaming"
        return "general"

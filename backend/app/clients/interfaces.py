"""Client interfaces for pluggable external integrations."""

from typing import Any, Dict, List, Optional, Protocol

from app.schemas.product import Product
from app.schemas.response import InterpretedRequest


class InterpretationClient(Protocol):
    """Interface for NL query interpretation providers."""

    def interpret_query(self, query: str, top_n: int) -> Optional[Dict[str, Any]]:
        """Return structured interpretation fields or None if unavailable."""


class ReportGenerationClient(Protocol):
    """Interface for recommendation narrative generation providers."""

    def generate_reasoning(
        self,
        query: str,
        interpreted: InterpretedRequest,
        best_pick: Optional[Product],
        alternatives: List[Product],
    ) -> Optional[str]:
        """Return natural-language reasoning text or None if unavailable."""


class StoreAutomationClient(Protocol):
    """Interface for store automation providers."""

    def run_store_workflow(
        self,
        site: str,
        interpreted_request: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Run workflow for a store and return raw product objects."""

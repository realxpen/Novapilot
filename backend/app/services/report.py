"""Final response/report generation service."""

from typing import List, Optional

from app.clients.interfaces import ReportGenerationClient
from app.schemas.product import Product
from app.schemas.response import ExecutionLogItem, InterpretedRequest, NovaPilotResponse


class ReportService:
    """Create frontend-friendly API response payloads."""

    def __init__(self, report_client: Optional[ReportGenerationClient] = None) -> None:
        self.report_client = report_client

    def generate(
        self,
        query: str,
        interpreted: InterpretedRequest,
        ranked_products: List[Product],
        top_n: int,
        execution_log: List[ExecutionLogItem],
        warnings: List[str],
    ) -> NovaPilotResponse:
        """Build final `NovaPilotResponse` with best pick and alternatives."""
        top_products = ranked_products[:top_n]
        best_pick = top_products[0] if top_products else None
        alternatives = top_products[1:] if len(top_products) > 1 else []

        reasoning = self._build_reasoning(query, interpreted, best_pick, alternatives)

        status = "success"
        if warnings:
            status = "partial_success"

        return NovaPilotResponse(
            status=status,
            query=query,
            interpreted_request=interpreted,
            execution_log=execution_log,
            best_pick=best_pick,
            alternatives=alternatives,
            comparison_table=top_products,
            reasoning=reasoning,
            warnings=warnings or None,
        )

    def _build_reasoning(
        self,
        query: str,
        interpreted: InterpretedRequest,
        best_pick: Optional[Product],
        alternatives: List[Product],
    ) -> str:
        if self.report_client:
            generated = self.report_client.generate_reasoning(
                query=query,
                interpreted=interpreted,
                best_pick=best_pick,
                alternatives=alternatives,
            )
            if generated:
                return generated

        if best_pick:
            return (
                f"{best_pick.name} was selected as the best option because it scored highest for "
                f"{interpreted.use_case}, with strong specs and price-to-performance balance."
            )
        return "No strong recommendation available because product data was insufficient."

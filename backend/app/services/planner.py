"""Deterministic planner for building store execution steps."""

from typing import List

from app.schemas.response import InterpretedRequest, PlanResult


class PlanningService:
    """Build a simple step-by-step plan from interpreted intent and sites."""

    def build_plan(self, interpreted: InterpretedRequest, supported_sites: List[str]) -> PlanResult:
        """Return deterministic pipeline steps for the selected stores."""
        steps: List[str] = []
        for site in supported_sites:
            steps.append(f"search_{site}")
            steps.append(f"collect_{site}_products")
        steps.extend(["normalize_products", "rank_products", "generate_report"])
        return PlanResult(steps=steps)

"""Response schemas for NovaPilot API routes."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.product import Product


class InterpretedRequest(BaseModel):
    """Structured interpretation of the natural-language user query."""

    category: str
    budget_currency: str
    budget_max: Optional[float] = None
    use_case: str
    priority_specs: List[str] = Field(default_factory=list)
    top_n: int = 3


class PlanResult(BaseModel):
    """Execution plan produced by the planner service."""

    steps: List[str]


class ExecutionLogItem(BaseModel):
    """Structured timeline log item for frontend progress rendering."""

    step_id: str
    label: str
    status: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class NovaPilotResponse(BaseModel):
    """Main API response for `/api/run-novapilot`."""

    status: str
    query: str
    interpreted_request: InterpretedRequest
    execution_log: List[ExecutionLogItem]
    best_pick: Optional[Product]
    alternatives: List[Product]
    comparison_table: List[Product]
    reasoning: str
    warnings: Optional[List[str]] = None

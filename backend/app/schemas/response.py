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


class InstantGuidance(BaseModel):
    """Fast advisory response shown before the live market report completes."""

    headline: str
    summary: str
    key_specs: List[str] = Field(default_factory=list)
    target_models: List[str] = Field(default_factory=list)
    featured_recommendations: List[str] = Field(default_factory=list)
    market_insights: List[str] = Field(default_factory=list)
    budget_bands: List[str] = Field(default_factory=list)
    budget_note: str
    selected_sites: List[str] = Field(default_factory=list)
    next_step: str


class JobSubmissionResponse(BaseModel):
    """Response returned immediately after a report job is queued."""

    job_id: str
    status: str
    query: str
    interpreted_request: InterpretedRequest
    instant_guidance: InstantGuidance
    current_step: Optional[str] = None
    execution_log: List[ExecutionLogItem] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    """Polling response for a running or completed report job."""

    job_id: str
    status: str
    query: str
    interpreted_request: InterpretedRequest
    instant_guidance: InstantGuidance
    current_step: Optional[str] = None
    execution_log: List[ExecutionLogItem] = Field(default_factory=list)
    final_report: Optional[NovaPilotResponse] = None
    error: Optional[str] = None

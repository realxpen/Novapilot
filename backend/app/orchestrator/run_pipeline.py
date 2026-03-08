"""Main orchestration flow for NovaPilot pipeline."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.clients.bedrock_client import BedrockClient
from app.config import get_settings
from app.schemas.request import RunNovaPilotRequest
from app.schemas.response import ExecutionLogItem, NovaPilotResponse
from app.services.automation import AutomationService
from app.services.extractor import ExtractionService
from app.services.interpreter import InterpreterService
from app.services.planner import PlanningService
from app.services.ranking import RankingService
from app.services.report import ReportService
from app.utils.logger import get_logger


logger = get_logger(__name__)
settings = get_settings()


class NovaPilotOrchestrator:
    """Coordinates interpretation, planning, automation, extraction, ranking, reporting."""

    def __init__(self) -> None:
        bedrock_client = BedrockClient()
        interpretation_client = bedrock_client if settings.use_bedrock_interpretation else None
        report_client = bedrock_client if settings.use_bedrock_report_generation else None

        self.interpreter = InterpreterService(interpretation_client=interpretation_client)
        self.planner = PlanningService()
        self.automation = AutomationService(use_nova_act=settings.use_nova_act_automation)
        self.extractor = ExtractionService()
        self.ranking = RankingService()
        self.report = ReportService(report_client=report_client)

    def run(self, request: RunNovaPilotRequest) -> NovaPilotResponse:
        """Run full synchronous MVP pipeline."""
        execution_log: list[ExecutionLogItem] = []
        warnings: list[str] = []

        self._log(
            execution_log,
            step_id="request_validation",
            label="Validate request payload",
            status="completed",
            details={"query_length": len(request.query), "site_count": len(request.supported_sites)},
        )

        self._log(
            execution_log,
            step_id="interpretation",
            label="Interpret shopping query",
            status="started",
        )
        interpreted = self.interpreter.interpret(request.query, request.top_n)
        self._log(
            execution_log,
            step_id="interpretation",
            label="Interpret shopping query",
            status="completed",
            details={
                "category": interpreted.category,
                "use_case": interpreted.use_case,
                "budget_max": interpreted.budget_max,
            },
        )

        self._log(
            execution_log,
            step_id="planning",
            label="Build execution plan",
            status="started",
        )
        plan = self.planner.build_plan(interpreted, request.supported_sites)
        self._log(
            execution_log,
            step_id="planning",
            label="Build execution plan",
            status="completed",
            details={"steps_count": len(plan.steps), "steps": plan.steps},
        )

        all_products = []
        for site in request.supported_sites:
            try:
                self._log(
                    execution_log,
                    step_id=f"automation_{site}",
                    label=f"Run {site} store automation",
                    status="started",
                )
                raw = self.automation.run_site_workflow(site, interpreted)
                self._log(
                    execution_log,
                    step_id=f"automation_{site}",
                    label=f"Run {site} store automation",
                    status="completed",
                    details={"raw_products_collected": len(raw)},
                )

                self._log(
                    execution_log,
                    step_id=f"normalization_{site}",
                    label=f"Normalize {site} products",
                    status="started",
                )
                normalized = self.extractor.normalize_products(site, raw)
                self._log(
                    execution_log,
                    step_id=f"normalization_{site}",
                    label=f"Normalize {site} products",
                    status="completed",
                    details={"normalized_products": len(normalized)},
                )
                all_products.extend(normalized)
            except Exception as exc:  # noqa: BLE001 - graceful fallback required by MVP
                warning = f"{site} workflow failed: {exc}"
                warnings.append(warning)
                self._log(
                    execution_log,
                    step_id=f"automation_{site}",
                    label=f"Run {site} store automation",
                    status="failed",
                    details={"error": str(exc)},
                )
                logger.warning(warning)

        if not all_products:
            warnings.append("No products were collected from selected stores.")
            return self.report.generate(
                query=request.query,
                interpreted=interpreted,
                ranked_products=[],
                top_n=request.top_n,
                execution_log=execution_log,
                warnings=warnings,
            )

        try:
            self._log(
                execution_log,
                step_id="ranking",
                label="Rank products",
                status="started",
                details={"input_products": len(all_products)},
            )
            ranked = self.ranking.rank(all_products, interpreted)
            self._log(
                execution_log,
                step_id="ranking",
                label="Rank products",
                status="completed",
                details={"ranked_products": len(ranked)},
            )
        except Exception as exc:  # noqa: BLE001 - partial response fallback
            warning = f"Ranking failed, returning unranked products: {exc}"
            warnings.append(warning)
            self._log(
                execution_log,
                step_id="ranking",
                label="Rank products",
                status="failed",
                details={"error": str(exc)},
            )
            ranked = all_products

        self._log(
            execution_log,
            step_id="report_generation",
            label="Generate recommendation report",
            status="completed",
            details={"top_n": request.top_n},
        )
        return self.report.generate(
            query=request.query,
            interpreted=interpreted,
            ranked_products=ranked,
            top_n=request.top_n,
            execution_log=execution_log,
            warnings=warnings,
        )

    def _log(
        self,
        execution_log: list[ExecutionLogItem],
        step_id: str,
        label: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        execution_log.append(
            ExecutionLogItem(
                step_id=step_id,
                label=label,
                status=status,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details=details,
            )
        )

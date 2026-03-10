"""Main orchestration flow for NovaPilot pipeline."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.clients.bedrock_client import BedrockClient
from app.config import get_settings
from app.schemas.request import RunNovaPilotRequest
from app.schemas.response import ExecutionLogItem, InterpretedRequest, NovaPilotResponse
from app.services.automation import AutomationService
from app.services.extractor import ExtractionService
from app.services.interpreter import InterpreterService
from app.services.planner import PlanningService
from app.services.ranking import RankingService
from app.services.report import ReportService
from app.services.site_recommendation import SiteRecommendationService
from app.utils.logger import get_logger


logger = get_logger(__name__)
settings = get_settings()


class NovaPilotOrchestrator:
    """Coordinates interpretation, planning, automation, extraction, ranking, reporting."""

    SITE_ALIASES: dict[str, tuple[str, ...]] = {
        "jumia": ("jumia",),
        "amazon": ("amazon",),
        "konga": ("konga",),
        "slot": ("slot",),
        "jiji": ("jiji",),
    }

    def __init__(self) -> None:
        bedrock_client = BedrockClient()
        interpretation_client = bedrock_client if settings.use_bedrock_interpretation else None
        report_client = bedrock_client if settings.use_bedrock_report_generation else None
        site_recommendation_client = bedrock_client if settings.use_bedrock_site_selection else None

        self.interpreter = InterpreterService(interpretation_client=interpretation_client)
        self.site_recommendation = SiteRecommendationService(
            recommendation_client=site_recommendation_client,
        )
        self.planner = PlanningService()
        self.automation = AutomationService(
            use_nova_act=settings.use_nova_act_automation,
            strict_live_mode=settings.nova_act_strict_mode,
        )
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

        selected_sites, site_selection_meta = self._resolve_sites(
            query=request.query,
            requested_sites=request.supported_sites,
            user_location=request.user_location,
            interpreted=interpreted,
            warnings=warnings,
        )
        self._log(
            execution_log,
            step_id="site_selection",
            label="Select target stores",
            status="completed",
            details=site_selection_meta,
        )

        self._log(
            execution_log,
            step_id="planning",
            label="Build execution plan",
            status="started",
        )
        plan = self.planner.build_plan(interpreted, selected_sites)
        self._log(
            execution_log,
            step_id="planning",
            label="Build execution plan",
            status="completed",
            details={"steps_count": len(plan.steps), "steps": plan.steps},
        )

        all_products = []
        for site in selected_sites:
            try:
                self._log(
                    execution_log,
                    step_id=f"automation_{site}",
                    label=f"Run {site} store automation",
                    status="started",
                )
                raw = self.automation.run_site_workflow(
                    site=site,
                    interpreted=interpreted,
                    query=request.query,
                    user_location=request.user_location,
                )
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

    def _resolve_sites(
        self,
        query: str,
        requested_sites: list[str],
        user_location: Optional[str],
        interpreted: InterpretedRequest,
        warnings: list[str],
    ) -> tuple[list[str], dict[str, Any]]:
        """Choose sites in priority order: explicit query > recommendation > defaults."""
        query_lower = query.lower()
        allowed_sites = [site.strip().lower() for site in requested_sites if site.strip()]
        if not allowed_sites:
            allowed_sites = list(settings.default_supported_sites)
        if settings.use_nova_act_automation:
            live_enabled_sites = self._get_live_enabled_sites()
            allowed_sites = [site for site in allowed_sites if site in live_enabled_sites]
        mentioned: list[str] = []
        for site, aliases in self.SITE_ALIASES.items():
            if any(alias in query_lower for alias in aliases):
                mentioned.append(site)

        if mentioned:
            unsupported_mentions = [site for site in mentioned if site not in allowed_sites]
            if unsupported_mentions:
                warnings.append(
                    "Ignored unsupported site mention(s): "
                    + ", ".join(sorted(set(unsupported_mentions)))
                )

            selected = [site for site in mentioned if site in allowed_sites]
            final_sites = selected or allowed_sites
            return final_sites, {
                "selected_sites": final_sites,
                "source": "explicit",
                "allowed_sites": allowed_sites,
            }

        recommendation = self.site_recommendation.recommend(
            query=query,
            interpreted=interpreted,
            allowed_sites=allowed_sites,
            user_location=user_location,
        )
        recommended_sites = recommendation.get("sites", [])
        if recommended_sites:
            meta = {
                "selected_sites": recommended_sites,
                "source": recommendation.get("source", "fallback"),
                "allowed_sites": allowed_sites,
                "confidence": recommendation.get("confidence"),
                "rationale": recommendation.get("rationale"),
            }
            excluded_sites = recommendation.get("excluded_sites")
            if excluded_sites:
                meta["excluded_sites"] = excluded_sites
            return recommended_sites, meta

        return allowed_sites, {
            "selected_sites": allowed_sites,
            "source": "defaults",
            "allowed_sites": allowed_sites,
        }

    def _get_live_enabled_sites(self) -> list[str]:
        site_workflows = {
            "amazon": settings.nova_act_workflow_amazon,
            "jumia": settings.nova_act_workflow_jumia,
            "konga": settings.nova_act_workflow_konga,
            "slot": settings.nova_act_workflow_slot,
            "jiji": settings.nova_act_workflow_jiji,
        }
        enabled = [site for site, workflow in site_workflows.items() if workflow.strip()]
        return enabled or ["amazon", "jumia"]

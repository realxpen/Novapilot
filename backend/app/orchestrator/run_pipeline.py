"""Main orchestration flow for NovaPilot pipeline."""

import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from app.clients.bedrock_client import BedrockClient
from app.config import get_settings
from app.schemas.request import RunNovaPilotRequest
from app.schemas.response import (
    ExecutionLogItem,
    InstantGuidance,
    InterpretedRequest,
    NovaPilotResponse,
)
from app.services.automation import AutomationService
from app.services.extractor import ExtractionService
from app.services.interpreter import InterpreterService
from app.services.planner import PlanningService
from app.services.ranking import RankingService
from app.services.report import ReportService
from app.services.site_recommendation import SiteRecommendationService
from app.utils.currency import convert_amount
from app.utils.logger import get_logger


logger = get_logger(__name__)
settings = get_settings()


class NovaPilotOrchestrator:
    """Coordinates interpretation, planning, automation, extraction, ranking, reporting."""

    SITE_ALIASES: dict[str, tuple[str, ...]] = {
        "jumia": ("jumia",),
        "amazon": ("amazon",),
    }

    def __init__(self) -> None:
        bedrock_client = BedrockClient()
        interpretation_client = bedrock_client if settings.use_bedrock_interpretation else None
        report_client = bedrock_client if settings.use_bedrock_report_generation else None
        site_recommendation_client = bedrock_client if settings.use_bedrock_site_selection else None
        self.guidance_client = bedrock_client if settings.use_bedrock_report_generation else None

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

    def run(
        self,
        request: RunNovaPilotRequest,
        progress_callback: Optional[Callable[[list[ExecutionLogItem], str], None]] = None,
    ) -> NovaPilotResponse:
        """Run full synchronous MVP pipeline."""
        execution_log: list[ExecutionLogItem] = []
        warnings: list[str] = []
        self._debug_event("incoming_request_payload", request.model_dump(mode="json"))

        self._log(
            execution_log,
            step_id="request_validation",
            label="Validate request payload",
            status="completed",
            details={"query_length": len(request.query), "site_count": len(request.supported_sites)},
            progress_callback=progress_callback,
        )

        self._log(
            execution_log,
            step_id="interpretation",
            label="Interpret shopping query",
            status="started",
            progress_callback=progress_callback,
        )
        interpreted = self.interpreter.interpret(request.query, request.top_n)
        self._debug_event("interpreted_request", interpreted)
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
            progress_callback=progress_callback,
        )

        selected_sites, site_selection_meta = self._resolve_sites(
            query=request.query,
            requested_sites=request.supported_sites,
            user_location=request.user_location,
            interpreted=interpreted,
            warnings=warnings,
        )
        self._debug_event(
            "supported_sites_used",
            {
                "requested_sites": request.supported_sites,
                "selected_sites": selected_sites,
                "site_selection_meta": site_selection_meta,
            },
        )
        self._log(
            execution_log,
            step_id="site_selection",
            label="Select target stores",
            status="completed",
            details=site_selection_meta,
            progress_callback=progress_callback,
        )

        self._log(
            execution_log,
            step_id="planning",
            label="Build execution plan",
            status="started",
            progress_callback=progress_callback,
        )
        plan = self.planner.build_plan(interpreted, selected_sites)
        self._debug_event("execution_plan", plan)
        self._log(
            execution_log,
            step_id="planning",
            label="Build execution plan",
            status="completed",
            details={"steps_count": len(plan.steps), "steps": plan.steps},
            progress_callback=progress_callback,
        )

        all_products = []
        for site in selected_sites:
            try:
                self._log(
                    execution_log,
                    step_id=f"automation_{site}",
                    label=f"Run {site} store automation",
                    status="started",
                    progress_callback=progress_callback,
                )
                automation_result = self.automation.run_site_workflow(
                    site=site,
                    interpreted=interpreted,
                    query=request.query,
                    user_location=request.user_location,
                )
                raw = automation_result.raw_products
                if automation_result.live_error_message:
                    self._add_warning(
                        warnings,
                        f"{self._site_label(site)} automation failed before extraction: "
                        f"{self._summarize_failure(automation_result.live_error_message)}"
                    )
                if automation_result.warning_message:
                    self._add_warning(warnings, automation_result.warning_message)
                self._debug_event(
                    f"raw_store_results_{site}",
                    {
                        "site": site,
                        "source": automation_result.source,
                        "warning_message": automation_result.warning_message,
                        "live_error_message": automation_result.live_error_message,
                        "count": len(raw),
                        "products": raw,
                    },
                )
                self._log(
                    execution_log,
                    step_id=f"automation_{site}",
                    label=f"Run {site} store automation",
                    status="completed",
                    details={
                        "raw_products_collected": len(raw),
                        "source": automation_result.source,
                    },
                    progress_callback=progress_callback,
                )
                if not raw:
                    self._add_warning(
                        warnings,
                        f"{self._site_label(site)} returned zero raw matching products before normalization."
                    )

                self._log(
                    execution_log,
                    step_id=f"normalization_{site}",
                    label=f"Normalize {site} products",
                    status="started",
                    progress_callback=progress_callback,
                )
                normalized = self.extractor.normalize_products(site, raw)
                self._debug_event(
                    f"normalized_products_{site}",
                    {
                        "site": site,
                        "count": len(normalized),
                        "products": normalized,
                    },
                )
                if raw and not normalized:
                    self._add_warning(
                        warnings,
                        f"{self._site_label(site)} returned raw results, but none could be normalized into valid product objects."
                    )
                self._log(
                    execution_log,
                    step_id=f"normalization_{site}",
                    label=f"Normalize {site} products",
                    status="completed",
                    details={"normalized_products": len(normalized)},
                    progress_callback=progress_callback,
                )
                filtered = self._filter_products(
                    normalized,
                    interpreted,
                    allow_invalid_urls=False,
                )
                self._debug_event(
                    f"products_after_filter_{site}",
                    {
                        "site": site,
                        "source": automation_result.source,
                        "count": len(filtered),
                        "products": filtered,
                    },
                )
                if normalized and not filtered:
                    self._add_warning(
                        warnings,
                        f"{self._site_label(site)} returned valid listings, but none passed the configured filters."
                    )
                self._log(
                    execution_log,
                    step_id=f"filtering_{site}",
                    label=f"Filter {site} products against intent",
                    status="completed",
                    details={
                        "before_count": len(normalized),
                        "after_count": len(filtered),
                    },
                    progress_callback=progress_callback,
                )
                all_products.extend(filtered)
            except Exception as exc:  # noqa: BLE001 - graceful fallback required by MVP
                warning = (
                    f"{self._site_label(site)} automation failed before extraction: "
                    f"{self._summarize_failure(str(exc))}"
                )
                self._add_warning(warnings, warning)
                self._debug_event(
                    f"store_failure_{site}",
                    {"site": site, "error": str(exc), "warnings": warnings},
                )
                self._log(
                    execution_log,
                    step_id=f"automation_{site}",
                    label=f"Run {site} store automation",
                    status="failed",
                    details={"error": str(exc)},
                    progress_callback=progress_callback,
                )
                logger.warning(warning)

        if not all_products:
            if not warnings:
                warnings.append("No products were collected from selected stores.")
            report = self.report.generate(
                query=request.query,
                interpreted=interpreted,
                ranked_products=[],
                top_n=request.top_n,
                execution_log=execution_log,
                warnings=warnings,
            )
            self._debug_event(
                "final_report_payload",
                {
                    "status": report.status,
                    "warnings": report.warnings,
                    "payload": report,
                },
            )
            return report

        try:
            self._log(
                execution_log,
                step_id="ranking",
                label="Rank products",
                status="started",
                details={"input_products": len(all_products)},
                progress_callback=progress_callback,
            )
            ranked = self.ranking.rank(all_products, interpreted)
            self._debug_event(
                "ranked_products",
                {
                    "count": len(ranked),
                    "products": ranked,
                },
            )
            self._log(
                execution_log,
                step_id="ranking",
                label="Rank products",
                status="completed",
                details={"ranked_products": len(ranked)},
                progress_callback=progress_callback,
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
                progress_callback=progress_callback,
            )
            ranked = all_products

        self._log(
            execution_log,
            step_id="report_generation",
            label="Generate recommendation report",
            status="completed",
            details={"top_n": request.top_n},
            progress_callback=progress_callback,
        )
        report = self.report.generate(
            query=request.query,
            interpreted=interpreted,
            ranked_products=ranked,
            top_n=request.top_n,
            execution_log=execution_log,
            warnings=warnings,
        )
        self._debug_event(
            "final_report_payload",
            {
                "status": report.status,
                "warnings": report.warnings,
                "payload": report,
            },
        )
        return report

    def build_instant_guidance(self, request: RunNovaPilotRequest) -> dict[str, Any]:
        """Build the immediate advisory payload shown before live extraction completes."""
        interpreted = self.interpreter.interpret(request.query, request.top_n)
        selected_sites, _ = self._resolve_sites(
            query=request.query,
            requested_sites=request.supported_sites,
            user_location=request.user_location,
            interpreted=interpreted,
            warnings=[],
        )
        return {
            "interpreted_request": interpreted,
            "instant_guidance": self._build_guidance_payload(
                query=request.query,
                interpreted=interpreted,
                selected_sites=selected_sites,
            ),
        }

    def _log(
        self,
        execution_log: list[ExecutionLogItem],
        step_id: str,
        label: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[list[ExecutionLogItem], str], None]] = None,
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
        if progress_callback:
            progress_callback(execution_log, label)

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

        # If the user did not explicitly name a store, search all enabled live stores
        # instead of narrowing to a single marketplace. This keeps Amazon and Jumia in
        # the same run by default.
        return allowed_sites, {
            "selected_sites": allowed_sites,
            "source": "automatic_all",
            "allowed_sites": allowed_sites,
            "rationale": "No specific store was mentioned, so all enabled supported stores were searched.",
        }

    def _build_guidance_payload(
        self,
        query: str,
        interpreted: InterpretedRequest,
        selected_sites: list[str],
    ) -> InstantGuidance:
        budget_text = (
            f"{interpreted.budget_currency} {int(interpreted.budget_max):,}"
            if interpreted.budget_max
            else interpreted.budget_currency
        )
        target_models = self._suggest_target_models(interpreted)
        spec_map = {
            "laptop": ["16GB RAM", "512GB SSD", "Intel Core i5/i7 or Ryzen 5/7"],
            "tablet": ["8GB RAM", "128GB+ storage", "sharp display with stylus support"],
            "smartphone": ["8GB RAM", "256GB storage", "strong battery and software support"],
            "audio": ["good driver quality", "solid battery life", "reliable microphone/noise control"],
        }
        key_specs = spec_map.get(interpreted.category, ["strong price-to-performance", "reliable ratings"])
        featured_recommendations = self._build_featured_recommendations(interpreted)
        market_insights = self._build_market_insights(interpreted)
        budget_bands = self._build_budget_bands(interpreted)
        fallback = InstantGuidance(
            headline=f"Best-fit guidance for {query}",
            summary=(
                f"For {interpreted.use_case}, focus on {', '.join(key_specs[:2])}. "
                f"The live market report is now checking {', '.join(selected_sites)} for exact listings."
            ),
            key_specs=key_specs,
            target_models=target_models,
            featured_recommendations=featured_recommendations,
            market_insights=market_insights,
            budget_bands=budget_bands,
            budget_note=f"Budget target: {budget_text}. Used or refurbished premium models may outperform brand-new low-tier options.",
            selected_sites=selected_sites,
            next_step="The detailed market report is running now. Keep this page open to receive the best live listings.",
        )
        generated = self._try_generate_instant_guidance(query, interpreted, selected_sites)
        if not generated:
            return fallback

        return InstantGuidance(
            headline=str(generated.get("headline") or fallback.headline),
            summary=str(generated.get("summary") or fallback.summary),
            key_specs=self._normalize_string_list(generated.get("key_specs"), fallback.key_specs),
            target_models=self._normalize_string_list(generated.get("target_models"), fallback.target_models),
            featured_recommendations=self._normalize_string_list(
                generated.get("featured_recommendations"),
                fallback.featured_recommendations,
            ),
            market_insights=self._normalize_string_list(
                generated.get("market_insights"),
                fallback.market_insights,
            ),
            budget_bands=self._normalize_string_list(generated.get("budget_bands"), fallback.budget_bands),
            budget_note=str(generated.get("budget_note") or fallback.budget_note),
            selected_sites=selected_sites,
            next_step=str(generated.get("next_step") or fallback.next_step),
        )

    def _suggest_target_models(self, interpreted: InterpretedRequest) -> list[str]:
        if interpreted.category == "laptop" and interpreted.use_case == "programming":
            return [
                "Dell Latitude 7490 / 7400",
                "HP EliteBook 840 G6/G7",
                "Lenovo IdeaPad 3 / Dell Inspiron 15",
            ]
        if interpreted.category == "laptop" and interpreted.use_case == "ui/ux design":
            return [
                "HP Envy x360 14/15",
                "Dell Inspiron 14 / XPS 13",
                "Lenovo IdeaPad 5 / Yoga 7",
            ]
        if interpreted.category == "tablet" and interpreted.use_case == "ui/ux design":
            return [
                "iPad Air / iPad Pro",
                "Samsung Galaxy Tab S8 / S9",
                "Xiaomi Pad 6 / Redmi Pad Pro",
            ]
        if interpreted.category == "tablet":
            return [
                "Samsung Galaxy Tab A / S series",
                "Lenovo Tab P series",
                "Xiaomi Pad / Redmi Pad series",
            ]
        if interpreted.category == "smartphone":
            return ["Samsung Galaxy A series", "Google Pixel A series", "Redmi Note Pro"]
        if interpreted.category == "audio":
            return ["Sony WH series", "Soundcore Space series", "JBL Tune series"]
        if interpreted.category == "electronics":
            return [
                "Shortlist the best-rated current models",
                "Prioritize strong price-to-performance options",
                "Compare top listings with reliable reviews",
            ]
        return [
            "Shortlist the best-rated current models",
            "Prioritize strong price-to-performance options",
            "Compare top listings with reliable reviews",
        ]

    def _get_live_enabled_sites(self) -> list[str]:
        return ["amazon", "jumia"]

    def _filter_products(
        self,
        products: list[Any],
        interpreted: InterpretedRequest,
        allow_invalid_urls: bool = False,
    ) -> list[Any]:
        desired_min_results = min(max(int(interpreted.top_n or 3), 1), 3)
        strict_matches: list[Any] = []
        for product in products:
            if not allow_invalid_urls and not self._is_valid_product_url(product.url, product.store):
                self._log_product_drop(product, "invalid_product_url", "strict", interpreted)
                continue
            if not self._matches_category(product.name, interpreted.category):
                self._log_product_drop(product, "category_mismatch", "strict", interpreted)
                continue
            if product.price <= 0:
                self._log_product_drop(product, "non_positive_price", "strict", interpreted)
                continue
            comparable_price = self._price_in_budget_currency(product, interpreted)
            if interpreted.budget_max and comparable_price > interpreted.budget_max:
                self._log_product_drop(product, "over_budget", "strict", interpreted)
                continue
            strict_matches.append(product)

        if len(strict_matches) >= desired_min_results:
            self._debug_event(
                "filter_result_strict",
                {
                    "count": len(strict_matches),
                    "products": strict_matches,
                },
            )
            return strict_matches

        # If strict filtering returns too few live listings, supplement with relaxed matches
        # that still satisfy the hard constraints. This helps keep the final shortlist at 3-5
        # items without inventing synthetic products when one store under-delivers.
        self._debug_event(
            "filter_strict_empty_fallback_to_relaxed",
            {
                "input_count": len(products),
                "strict_count": len(strict_matches),
                "desired_min_results": desired_min_results,
                "category": interpreted.category,
                "budget_max": interpreted.budget_max,
            },
        )
        relaxed_matches: list[Any] = []
        seen_keys = {
            (
                (getattr(product, "store", "") or "").lower().strip(),
                (getattr(product, "name", "") or "").lower().strip(),
                (getattr(product, "url", "") or "").strip(),
            )
            for product in strict_matches
        }
        for product in products:
            product_key = (
                (getattr(product, "store", "") or "").lower().strip(),
                (getattr(product, "name", "") or "").lower().strip(),
                (getattr(product, "url", "") or "").strip(),
            )
            if product_key in seen_keys:
                continue
            if not allow_invalid_urls and not self._is_valid_product_url(product.url, product.store):
                self._log_product_drop(product, "invalid_product_url", "relaxed", interpreted)
                continue
            if self._is_blocked_for_category(product.name, interpreted.category):
                self._log_product_drop(product, "blocked_for_category", "relaxed", interpreted)
                continue
            if product.price <= 0:
                self._log_product_drop(product, "non_positive_price", "relaxed", interpreted)
                continue
            comparable_price = self._price_in_budget_currency(product, interpreted)
            if interpreted.budget_max and comparable_price > interpreted.budget_max:
                self._log_product_drop(product, "over_budget", "relaxed", interpreted)
                continue
            relaxed_matches.append(product)
            seen_keys.add(product_key)
        self._debug_event(
            "filter_result_relaxed",
            {
                "count": len(relaxed_matches),
                "products": relaxed_matches,
            },
        )
        combined_matches = strict_matches + relaxed_matches
        if combined_matches:
            self._debug_event(
                "filter_result_combined",
                {
                    "strict_count": len(strict_matches),
                    "relaxed_count": len(relaxed_matches),
                    "combined_count": len(combined_matches),
                    "products": combined_matches,
                },
            )
        return combined_matches

    def _matches_category(self, name: str, category: str) -> bool:
        lowered = name.lower()
        category_terms = {
            "laptop": [
                "laptop",
                "notebook",
                "ultrabook",
                "thinkpad",
                "elitebook",
                "latitude",
                "macbook",
                "ideapad",
                "inspiron",
                "probook",
                "zenbook",
            ],
            "smartphone": [
                "smartphone",
                "phone",
                "galaxy",
                "samsung",
                "iphone",
                "pixel",
                "redmi",
                "xiaomi",
                "infinix",
                "tecno",
                "oppo",
                "vivo",
                "realme",
                "oneplus",
                "nokia",
                "itel",
                "honor",
            ],
            "tablet": ["tablet", "ipad", "galaxy tab", "tab ", "redmi pad", "xiaomi pad", "lenovo tab"],
            "audio": ["headphone", "earbud", "earphone", "buds", "wh-", "tune "],
        }

        if self._is_blocked_for_category(name, category):
            return False

        expected = category_terms.get(category)
        if not expected:
            return True
        if any(term in lowered for term in expected):
            return True

        # Relaxed acceptance for terse marketplace titles that omit obvious product nouns.
        if category == "smartphone":
            phone_indicators = ["5g", "4g", "dual sim", "sim", "android", "ios"]
            storage_indicators = ["64gb", "128gb", "256gb", "512gb"]
            return any(token in lowered for token in phone_indicators + storage_indicators)
        if category == "tablet":
            return any(token in lowered for token in ["10.1", "11\"", "12.9", "stylus", "pen support"])
        if category == "laptop":
            return any(token in lowered for token in ["intel", "ryzen", "ssd", "ram"])
        return False

    def _is_blocked_for_category(self, name: str, category: str) -> bool:
        lowered = name.lower()
        blocked_terms = {
            "laptop": ["bag", "sleeve", "skin", "sticker", "backpack", "course", "book"],
            "smartphone": [
                "case",
                "cover",
                "screen protector",
                "charger",
                "earphone",
                "headset",
                "replacement",
                "housing",
                "tempered glass",
                "back cover",
                "power bank",
            ],
            "tablet": [
                "case",
                "cover",
                "keyboard case",
                "screen protector",
                "pen only",
                "stylus only",
                "tempered glass",
                "graphic tablet",
                "graphics tablet",
                "drawing tablet",
                "drawing pad",
                "pen tablet",
                "pen display",
                "digitizer",
                "wacom",
                "huion",
                "ugee",
                "xp-pen",
                "veikk",
            ],
            "audio": ["case", "cover", "speaker", "microphone", "cable", "adapter"],
        }
        return any(blocked in lowered for blocked in blocked_terms.get(category, []))

    def _is_valid_product_url(self, url: str | None, store: str) -> bool:
        if not url:
            return False
        lowered = url.lower().strip()
        if not lowered.startswith("http://") and not lowered.startswith("https://"):
            return False

        store_key = (store or "").lower().strip()
        if store_key == "jumia":
            if "jumia.com.ng" not in lowered:
                return False
            if "/catalog/?" in lowered or "catalog/?q=" in lowered:
                return False
            if lowered in {"https://www.jumia.com.ng", "https://www.jumia.com.ng/"}:
                return False
            if ".html" not in lowered:
                return False
        if store_key == "amazon":
            if "amazon." not in lowered:
                return False
            if "/s?" in lowered and "k=" in lowered:
                return False
        return True

    def _build_featured_recommendations(self, interpreted: InterpretedRequest) -> list[str]:
        if interpreted.category == "smartphone":
            return [
                "Best overall: Samsung Galaxy A35 / A55 for balanced performance and display quality.",
                "Best value: Redmi Note 13 Pro or Tecno Camon 30 if camera and price matter most.",
                "Stretch pick: iPhone 13 if a clean used unit fits close to budget.",
            ]
        if interpreted.category == "laptop" and interpreted.use_case == "programming":
            return [
                "Best coding value: Dell Latitude 7490/7400 with 16GB RAM and SSD.",
                "Best business-grade option: HP EliteBook 840 G6/G7.",
                "Best value fallback: Lenovo IdeaPad 3 or Dell Inspiron 15 Core i5.",
            ]
        if interpreted.category == "tablet":
            return [
                "Best overall: iPad Air or iPad Pro for creative apps and accessory support.",
                "Best Android tablet: Galaxy Tab S8 / S9 for display quality and stylus workflows.",
                "Best value: Xiaomi Pad 6 or Redmi Pad Pro for price-to-performance.",
            ]
        if interpreted.category == "audio":
            return [
                "Best overall: Sony WH series for sound and noise cancellation.",
                "Best value: Soundcore Space series for features per price.",
                "Best mainstream pick: JBL Tune series for accessible daily use.",
            ]
        return [
            "Prioritize listings with strong ratings and realistic local pricing.",
            "Avoid accessories, bundle traps, and misleading category matches.",
            "Compare only a few strong candidates instead of many weak ones.",
        ]

    def _build_market_insights(self, interpreted: InterpretedRequest) -> list[str]:
        if interpreted.category == "smartphone":
            return [
                "Prices in Nigeria can shift quickly by seller, color, and imported stock.",
                "Used premium phones can outperform new low-tier devices in this budget range.",
                "Camera-focused Tecno, Redmi, and Galaxy A-series devices usually dominate mid-range value.",
            ]
        if interpreted.category == "laptop":
            return [
                "UK-used business laptops often beat brand-new entry-level machines on build quality.",
                "16GB RAM and SSD storage matter more than flashy branding for real work.",
                "Seller condition notes and battery health can change the real value dramatically.",
            ]
        if interpreted.category == "tablet":
            return [
                "Stylus support and display quality matter more than raw benchmark scores for design work.",
                "Official accessory availability can matter as much as the tablet itself.",
                "Older flagship tablets often outperform newer budget tablets.",
            ]
        return [
            "Real value usually comes from a small number of strong listings, not the biggest catalog.",
            "Ratings, seller quality, and spec honesty matter more than headline discounts.",
        ]

    def _build_budget_bands(self, interpreted: InterpretedRequest) -> list[str]:
        budget = interpreted.budget_max or 0
        currency = interpreted.budget_currency
        if interpreted.category == "smartphone":
            return [
                f"Sub-{currency} 200,000: entry-level phones focused on battery and basic daily use.",
                f"{currency} 200,000-{currency} 350,000: stronger mid-range balance for display and camera.",
                f"{currency} 350,000-{currency} {int(budget):,}" if budget else f"{currency} 350,000+: premium mid-range and older flagships.",
            ]
        if interpreted.category == "laptop":
            return [
                f"Sub-{currency} 400,000: basic productivity or older refurb units.",
                f"{currency} 400,000-{currency} 700,000: solid used business-class laptops.",
                f"{currency} 700,000-{currency} {int(budget):,}" if budget else f"{currency} 700,000+: stronger developer-focused configs.",
            ]
        if interpreted.category == "tablet":
            return [
                f"Sub-{currency} 250,000: entry Android tablets for media and light note-taking.",
                f"{currency} 250,000-{currency} 500,000: better displays and stronger app performance.",
                f"Above {currency} 500,000: flagship creative tablets and older iPad Pro tiers.",
            ]
        return [
            "Lower band: prioritize essentials and reliable sellers.",
            "Mid band: target the best price-to-performance listings.",
            "Upper band: shortlist the strongest premium options within reach.",
        ]

    def _try_generate_instant_guidance(
        self,
        query: str,
        interpreted: InterpretedRequest,
        selected_sites: list[str],
    ) -> Optional[Dict[str, Any]]:
        if not self.guidance_client or not hasattr(self.guidance_client, "generate_instant_guidance"):
            return None
        try:
            generated = self.guidance_client.generate_instant_guidance(
                query=query,
                interpreted=interpreted,
                selected_sites=selected_sites,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Instant guidance generation failed: %s", exc)
            return None
        return generated if isinstance(generated, dict) else None

    def _normalize_string_list(self, value: Any, fallback: list[str]) -> list[str]:
        if not isinstance(value, list):
            return fallback
        normalized = [str(item).strip() for item in value if str(item).strip()]
        return normalized or fallback

    def _log_product_drop(
        self,
        product: Any,
        reason: str,
        stage: str,
        interpreted: InterpretedRequest,
    ) -> None:
        self._debug_event(
            "dropped_product",
            {
                "stage": stage,
                "reason": reason,
                "category": interpreted.category,
                "budget_max": interpreted.budget_max,
                "product": product,
            },
        )

    def _price_in_budget_currency(
        self,
        product: Any,
        interpreted: InterpretedRequest,
    ) -> float:
        converted = convert_amount(
            getattr(product, "price", None),
            getattr(product, "currency", None),
            interpreted.budget_currency,
            settings.usd_to_ngn_rate,
        )
        if converted is not None:
            return converted
        return float(getattr(product, "price", 0.0) or 0.0)

    def _debug_event(self, label: str, payload: Any) -> None:
        logger.info(
            "NOVAPILOT_DEBUG %s\n%s",
            label,
            json.dumps(self._to_debug_value(payload), indent=2, ensure_ascii=False, default=str),
        )

    def _to_debug_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, list):
            return [self._to_debug_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._to_debug_value(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            return self._to_debug_value(value.model_dump(mode="json"))
        return value

    def _site_label(self, site: str) -> str:
        return site[:1].upper() + site[1:].lower()

    def _add_warning(self, warnings: list[str], warning: str) -> None:
        if warning and warning not in warnings:
            warnings.append(warning)

    def _summarize_failure(self, error_text: str) -> str:
        lowered = error_text.lower()
        if "failed to start the actuator" in lowered:
            return "Nova Act actuator could not start."
        if "actactuationerror" in lowered:
            return "Nova Act actuator could not start."
        if "actexceededmaxstepserror" in lowered:
            return "Nova Act exceeded maximum workflow steps."
        if "api.nova.amazon.com" in lowered and (
            "failed to establish a new connection" in lowered
            or "permissionerror" in lowered
            or "winerror 10013" in lowered
            or "max retries exceeded" in lowered
        ):
            return "Nova Act could not connect to api.nova.amazon.com."
        if "timed out" in lowered or "timeout" in lowered:
            return "Nova Act request timed out."
        if "acttimeouterror" in lowered:
            return "Nova Act request timed out."
        if "set nova_api_key" in lowered or "set nova_act_api_key" in lowered:
            return "Nova Act API key is missing."
        if "unauthorized" in lowered or "forbidden" in lowered or "invalid api key" in lowered:
            return "Nova Act authentication failed."
        for line in error_text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return error_text.strip() or "Unknown live automation failure."

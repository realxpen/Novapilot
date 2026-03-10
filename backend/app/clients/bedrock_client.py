"""Bedrock client for real Amazon Nova 2 Lite calls."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from app.clients.interfaces import (
    InterpretationClient,
    ReportGenerationClient,
    SiteRecommendationClient,
)
from app.schemas.product import Product
from app.schemas.response import InterpretedRequest
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BedrockClient(InterpretationClient, ReportGenerationClient, SiteRecommendationClient):
    """Amazon Bedrock adapter for query interpretation and reasoning generation.

    This class performs real Bedrock runtime calls when credentials and model access
    are correctly configured in AWS. If a call fails, it returns `None` so the
    pipeline fallback logic can continue.
    """

    def __init__(self) -> None:
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.interpret_model_id = os.getenv(
            "NOVAPILOT_BEDROCK_INTERPRET_MODEL_ID",
            "amazon.nova-lite-v1:0",
        )
        self.report_model_id = os.getenv(
            "NOVAPILOT_BEDROCK_REPORT_MODEL_ID",
            "amazon.nova-lite-v1:0",
        )
        self.site_selection_model_id = os.getenv(
            "NOVAPILOT_BEDROCK_SITE_SELECTION_MODEL_ID",
            "amazon.nova-lite-v1:0",
        )
        self._client = self._build_client()

    def interpret_query(self, query: str, top_n: int) -> Optional[Dict[str, Any]]:
        """Interpret user query into structured shopping intent via Bedrock."""
        if self._client is None:
            return None

        prompt = (
            "You are an e-commerce query parser. Return only valid JSON with keys: "
            "category, budget_currency, budget_max, use_case, priority_specs, top_n. "
            "budget_max must be number or null. priority_specs must be a JSON array of strings.\n"
            f"User query: {query}\n"
            f"top_n: {top_n}\n"
        )
        text = self._invoke_text_model(prompt=prompt, model_id=self.interpret_model_id)
        if not text:
            return None

        parsed = self._parse_json_object(text)
        if not parsed:
            logger.warning("Bedrock interpret response was not valid JSON: %s", text[:240])
            return None

        parsed["top_n"] = int(parsed.get("top_n", top_n))
        return parsed

    def generate_reasoning(
        self,
        query: str,
        interpreted: InterpretedRequest,
        best_pick: Optional[Product],
        alternatives: List[Product],
    ) -> Optional[str]:
        """Generate user-facing recommendation reasoning via Bedrock."""
        if self._client is None or best_pick is None:
            return None

        alt_names = [alt.name for alt in alternatives[:3]]
        prompt = (
            "You are NovaPilot, an e-commerce comparison assistant. "
            "Write a concise, clear explanation (2-4 sentences) for why the best product was selected.\n"
            f"Original query: {query}\n"
            f"Use case: {interpreted.use_case}\n"
            f"Budget max: {interpreted.budget_max}\n"
            f"Best pick: {best_pick.model_dump()}\n"
            f"Alternative names: {alt_names}\n"
            "Return plain text only."
        )
        text = self._invoke_text_model(prompt=prompt, model_id=self.report_model_id)
        return text.strip() if text else None

    def recommend_sites(
        self,
        query: str,
        user_location: Optional[str],
        category: str,
        budget_currency: str,
        budget_max: Optional[float],
        allowed_sites: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Recommend shopping sites via Bedrock."""
        if self._client is None or not allowed_sites:
            return None

        prompt = (
            "You are a shopping site selector. Return only valid JSON with keys: "
            "recommended_sites, excluded_sites, confidence, rationale. "
            "recommended_sites and excluded_sites must be JSON arrays of strings. "
            "confidence must be a number from 0 to 1. Keep recommendations within allowed_sites only. "
            "Prioritize location fit, category fit, budget fit, and likelihood of current availability. "
            "For Nigeria, usually prioritize jumia, konga, slot, and jiji when allowed, and include amazon only when relevant.\n"
            f"query: {query}\n"
            f"user_location: {user_location or 'unknown'}\n"
            f"category: {category}\n"
            f"budget_currency: {budget_currency}\n"
            f"budget_max: {budget_max}\n"
            f"allowed_sites: {allowed_sites}\n"
        )
        text = self._invoke_text_model(prompt=prompt, model_id=self.site_selection_model_id)
        if not text:
            return None

        parsed = self._parse_json_object(text)
        if not parsed:
            logger.warning("Bedrock site recommendation response was not valid JSON: %s", text[:240])
            return None
        return parsed

    def _build_client(self) -> Any:
        try:
            import boto3  # local import so app still runs without boto3 installed

            return boto3.client("bedrock-runtime", region_name=self.aws_region)
        except Exception as exc:  # noqa: BLE001 - caller uses graceful fallback
            logger.warning("Bedrock client init failed: %s", exc)
            return None

    def _invoke_text_model(self, prompt: str, model_id: str) -> Optional[str]:
        if self._client is None:
            return None

        # Primary path: Bedrock Converse API (recommended for Nova models).
        try:
            response = self._client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"temperature": 0.1, "maxTokens": 600},
            )
            return self._extract_text_from_converse_response(response)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bedrock converse call failed for %s: %s", model_id, exc)

        # Fallback path: invoke_model with generic messages JSON structure.
        try:
            payload = {
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"temperature": 0.1, "maxTokens": 600},
            }
            response = self._client.invoke_model(
                modelId=model_id,
                body=json.dumps(payload).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )
            body = response.get("body")
            if body is None:
                return None
            raw = body.read().decode("utf-8")
            data = json.loads(raw)
            return self._extract_text_from_generic_response(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bedrock invoke_model call failed for %s: %s", model_id, exc)
            return None

    def _extract_text_from_converse_response(self, response: Dict[str, Any]) -> Optional[str]:
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])
        for part in content:
            text = part.get("text")
            if text:
                return text
        return None

    def _extract_text_from_generic_response(self, data: Dict[str, Any]) -> Optional[str]:
        # Handles common Bedrock output envelopes across models.
        if "output" in data and isinstance(data["output"], dict):
            message = data["output"].get("message", {})
            content = message.get("content", [])
            for part in content:
                text = part.get("text")
                if text:
                    return text
        if "content" in data and isinstance(data["content"], list):
            for part in data["content"]:
                text = part.get("text")
                if text:
                    return text
        if "generation" in data and isinstance(data["generation"], str):
            return data["generation"]
        if "text" in data and isinstance(data["text"], str):
            return data["text"]
        return None

    def _parse_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Extract first JSON object if model wrapped it in prose/markdown.
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

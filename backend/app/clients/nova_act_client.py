"""Nova Act client using AWS IAM authentication via boto3."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.clients.interfaces import StoreAutomationClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NovaActClient(StoreAutomationClient):
    """AWS Nova Act workflow runner.

    This client uses AWS credentials from environment/SDK credential chain and does
    not require a Nova Act API key or custom REST endpoint.
    """

    TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT", "SUCCEEDED"}
    ACT_TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED"}

    def __init__(self) -> None:
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("NOVAPILOT_NOVA_ACT_MODEL_ID", "amazon.nova-act-v1:0")
        self.log_group_name = os.getenv("NOVAPILOT_NOVA_ACT_LOG_GROUP_NAME", "")
        self.poll_interval_seconds = float(os.getenv("NOVAPILOT_NOVA_ACT_POLL_INTERVAL_SECONDS", "2"))
        self.timeout_seconds = int(os.getenv("NOVAPILOT_NOVA_ACT_TIMEOUT_SECONDS", "90"))
        self.workflow_by_site = {
            "amazon": os.getenv("NOVAPILOT_NOVA_ACT_WORKFLOW_AMAZON", "novapilot_search_amazon"),
            "jumia": os.getenv("NOVAPILOT_NOVA_ACT_WORKFLOW_JUMIA", "novapilot_search_jumia"),
            "konga": os.getenv("NOVAPILOT_NOVA_ACT_WORKFLOW_KONGA", ""),
            "slot": os.getenv("NOVAPILOT_NOVA_ACT_WORKFLOW_SLOT", ""),
            "jiji": os.getenv("NOVAPILOT_NOVA_ACT_WORKFLOW_JIJI", ""),
        }
        self._nova_act = self._build_nova_act_client()
        self._s3 = self._build_s3_client()

    def run_store_workflow(self, site: str, interpreted_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a workflow run and return normalized raw product dictionaries."""
        if self._nova_act is None:
            raise RuntimeError("Nova Act boto3 client could not be initialized.")

        workflow_definition = self._resolve_workflow_name(site=site)
        run_id = self._create_workflow_run(workflow_definition_name=workflow_definition)
        session_id = self._create_session(
            workflow_definition_name=workflow_definition,
            workflow_run_id=run_id,
        )
        act_id = self._create_act(
            workflow_definition_name=workflow_definition,
            workflow_run_id=run_id,
            session_id=session_id,
            task=self._build_task(site=site, interpreted_request=interpreted_request),
        )
        act_summary = self._wait_for_act_completion(
            workflow_definition_name=workflow_definition,
            workflow_run_id=run_id,
            session_id=session_id,
            act_id=act_id,
        )
        status = str(act_summary.get("status", "")).upper()
        if status != "SUCCEEDED":
            raise RuntimeError(f"Workflow act {act_id} finished with status: {status}")

        run_details = self._get_workflow_run(
            workflow_definition_name=workflow_definition,
            workflow_run_id=run_id,
        )

        products = self._extract_products_from_run(
            site=site,
            workflow_definition_name=workflow_definition,
            workflow_run_id=run_id,
            run_details=run_details,
        )
        if not products:
            raise RuntimeError(f"No products extracted from workflow {workflow_definition}")
        return products

    def _build_nova_act_client(self) -> Any:
        try:
            import boto3

            return boto3.client("nova-act", region_name=self.aws_region)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nova Act client initialization failed: %s", exc)
            return None

    def _build_s3_client(self) -> Any:
        try:
            import boto3

            return boto3.client("s3", region_name=self.aws_region)
        except Exception:  # noqa: BLE001
            return None

    def _resolve_workflow_name(self, site: str) -> str:
        workflow = self.workflow_by_site.get(site.lower(), "")
        if not workflow:
            raise RuntimeError(f"No workflow definition configured for site '{site}'")
        return workflow

    def _create_workflow_run(self, workflow_definition_name: str) -> str:
        payload: Dict[str, Any] = {
            "workflowDefinitionName": workflow_definition_name,
            "clientInfo": {
                "compatibilityVersion": 1,
                "sdkVersion": "novapilot-backend-0.1.0",
            },
            "modelId": self.model_id,
        }
        if self.log_group_name:
            payload["logGroupName"] = self.log_group_name

        response = self._nova_act.create_workflow_run(**payload)
        workflow_run_id = response.get("workflowRunId")
        if not workflow_run_id:
            raise RuntimeError(f"create_workflow_run did not return workflowRunId: {response}")
        return str(workflow_run_id)

    def _create_session(self, workflow_definition_name: str, workflow_run_id: str) -> str:
        response = self._nova_act.create_session(
            workflowDefinitionName=workflow_definition_name,
            workflowRunId=workflow_run_id,
        )
        session_id = response.get("sessionId")
        if not session_id:
            raise RuntimeError(f"create_session did not return sessionId: {response}")
        return str(session_id)

    def _create_act(
        self,
        workflow_definition_name: str,
        workflow_run_id: str,
        session_id: str,
        task: str,
    ) -> str:
        response = self._nova_act.create_act(
            workflowDefinitionName=workflow_definition_name,
            workflowRunId=workflow_run_id,
            sessionId=session_id,
            task=task,
        )
        act_id = response.get("actId")
        if not act_id:
            raise RuntimeError(f"create_act did not return actId: {response}")
        return str(act_id)

    def _wait_for_act_completion(
        self,
        workflow_definition_name: str,
        workflow_run_id: str,
        session_id: str,
        act_id: str,
    ) -> Dict[str, Any]:
        deadline = time.time() + self.timeout_seconds
        last_summary: Dict[str, Any] = {}
        while time.time() < deadline:
            acts = self._list_acts(workflow_definition_name, workflow_run_id, session_id)
            for act in acts:
                if str(act.get("actId")) != act_id:
                    continue
                last_summary = act
                status = str(act.get("status", "")).upper()
                if status in self.ACT_TERMINAL_STATUSES:
                    return act
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(
            f"Act {act_id} timed out after {self.timeout_seconds}s. Last summary: {last_summary}"
        )

    def _get_workflow_run(self, workflow_definition_name: str, workflow_run_id: str) -> Dict[str, Any]:
        return self._nova_act.get_workflow_run(
            workflowDefinitionName=workflow_definition_name,
            workflowRunId=workflow_run_id,
        )

    def _wait_for_run_completion(self, workflow_definition_name: str, workflow_run_id: str) -> Dict[str, Any]:
        deadline = time.time() + self.timeout_seconds
        last_response: Dict[str, Any] = {}
        while time.time() < deadline:
            last_response = self._nova_act.get_workflow_run(
                workflowDefinitionName=workflow_definition_name,
                workflowRunId=workflow_run_id,
            )
            status = str(last_response.get("status", "")).upper()
            if status in self.TERMINAL_STATUSES:
                return last_response
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(
            f"Workflow run {workflow_run_id} timed out after {self.timeout_seconds}s. "
            f"Last response: {last_response}"
        )

    def _build_task(self, site: str, interpreted_request: Dict[str, Any]) -> str:
        query = str(interpreted_request.get("query", "")).strip()
        if not query:
            raise RuntimeError("No user query was provided for live workflow execution.")

        location = str(interpreted_request.get("user_location") or "Nigeria").strip()
        category = str(interpreted_request.get("category") or "product").strip()
        budget_currency = str(interpreted_request.get("budget_currency") or "NGN").strip()
        budget_max = interpreted_request.get("budget_max")
        use_case = str(interpreted_request.get("use_case") or "general").strip()
        priority_specs = interpreted_request.get("priority_specs") or []
        specs_text = ", ".join(str(spec) for spec in priority_specs if str(spec).strip()) or "price, rating, relevance"
        budget_text = f"{budget_currency} {budget_max}" if budget_max else budget_currency

        if site.lower() == "amazon":
            return (
                f"Set Amazon delivery location to {location}. Search for '{query}'. "
                f"Focus on {category} products for {use_case}. Budget target: {budget_text}. "
                f"Open actual product detail pages only. Extract exact product_url, image_url, displayed price, "
                f"rating, and key details emphasizing {specs_text}. Return JSON products only."
            )

        return (
            f"Search {site} for '{query}' in {location}. Focus on {category} products for {use_case}. "
            f"Budget target: {budget_text}. Open actual product detail pages only. Extract exact product detail URL, "
            f"image URL, displayed price, rating, and key specs emphasizing {specs_text}. Return JSON products only."
        )

    def _extract_products_from_run(
        self,
        site: str,
        workflow_definition_name: str,
        workflow_run_id: str,
        run_details: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        # 1) Try direct payload extraction from run details.
        direct = self._find_product_candidates(run_details)
        if direct:
            return self._coerce_site_schema(site, direct)

        # 2) Try session/act summaries and optional S3 traces.
        sessions = self._list_sessions(workflow_definition_name, workflow_run_id)
        for session in sessions:
            session_id = session.get("sessionId")
            if not session_id:
                continue
            acts = self._list_acts(workflow_definition_name, workflow_run_id, str(session_id))
            for act in acts:
                inline_products = self._find_product_candidates(act)
                if inline_products:
                    return self._coerce_site_schema(site, inline_products)

                trace_location = self._extract_trace_location(act)
                if trace_location:
                    trace_payload = self._download_trace_payload(trace_location)
                    trace_products = self._find_product_candidates(trace_payload)
                    if trace_products:
                        return self._coerce_site_schema(site, trace_products)
        return []

    def _list_sessions(self, workflow_definition_name: str, workflow_run_id: str) -> List[Dict[str, Any]]:
        try:
            response = self._nova_act.list_sessions(
                workflowDefinitionName=workflow_definition_name,
                workflowRunId=workflow_run_id,
                sortOrder="Descending",
            )
            return list(response.get("sessionSummaries", []))
        except Exception as exc:  # noqa: BLE001
            logger.warning("list_sessions failed for run %s: %s", workflow_run_id, exc)
            return []

    def _list_acts(self, workflow_definition_name: str, workflow_run_id: str, session_id: str) -> List[Dict[str, Any]]:
        try:
            response = self._nova_act.list_acts(
                workflowDefinitionName=workflow_definition_name,
                workflowRunId=workflow_run_id,
                sessionId=session_id,
                sortOrder="Descending",
            )
            return list(response.get("actSummaries", []))
        except Exception as exc:  # noqa: BLE001
            logger.warning("list_acts failed for session %s: %s", session_id, exc)
            return []

    def _extract_trace_location(self, act: Dict[str, Any]) -> Optional[str]:
        trace = act.get("traceLocation")
        if isinstance(trace, dict):
            for key in ("location", "s3Uri", "uri"):
                value = trace.get(key)
                if isinstance(value, str):
                    return value
        if isinstance(trace, str):
            return trace
        return None

    def _download_trace_payload(self, location: str) -> Any:
        if self._s3 is None:
            return {}
        if not location.startswith("s3://"):
            return {}
        parsed = urlparse(location)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        if not bucket or not key:
            return {}
        try:
            obj = self._s3.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read().decode("utf-8")
            return json.loads(body)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read Nova Act trace from %s: %s", location, exc)
            return {}

    def _find_product_candidates(self, payload: Any) -> List[Dict[str, Any]]:
        if payload is None:
            return []
        if isinstance(payload, list):
            dict_items = [item for item in payload if isinstance(item, dict)]
            if dict_items and self._looks_like_product(dict_items[0]):
                return dict_items
            out: List[Dict[str, Any]] = []
            for item in dict_items:
                out.extend(self._find_product_candidates(item))
            return out
        if isinstance(payload, dict):
            for key in ("products", "results", "items", "data"):
                if key in payload:
                    found = self._find_product_candidates(payload[key])
                    if found:
                        return found
            for value in payload.values():
                found = self._find_product_candidates(value)
                if found:
                    return found
        return []

    def _looks_like_product(self, item: Dict[str, Any]) -> bool:
        keys = {k.lower() for k in item.keys()}
        return bool(keys & {"name", "title", "price", "price_text", "amount", "product_url", "url"})

    def _coerce_site_schema(self, site: str, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        site_key = site.lower()
        output: List[Dict[str, Any]] = []
        for item in products:
            if site_key == "amazon":
                output.append(
                    {
                        "name": item.get("name") or item.get("title") or "Unknown product",
                        "amount": item.get("amount") or item.get("price") or item.get("price_text") or "NGN 0",
                        "currency_code": item.get("currency_code") or item.get("currency") or "NGN",
                        "rating": item.get("rating"),
                        "details": item.get("details") or item.get("specs") or "",
                        "product_url": item.get("product_url") or item.get("url"),
                        "image_url": item.get("image_url") or item.get("image"),
                    }
                )
            elif site_key in {"jumia", "konga", "slot", "jiji"}:
                output.append(
                    {
                        "title": item.get("title") or item.get("name") or "Unknown product",
                        "price_text": item.get("price_text") or item.get("price") or item.get("amount") or "NGN 0",
                        "currency": item.get("currency") or item.get("currency_code") or "NGN",
                        "rating_text": str(item.get("rating")) if item.get("rating") is not None else None,
                        "specs": item.get("specs") or item.get("details") or "",
                        "url": item.get("url") or item.get("product_url"),
                        "image": item.get("image") or item.get("image_url"),
                    }
                )
            else:
                output.append(item)
        return output

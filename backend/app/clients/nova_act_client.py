"""Nova Act client backed by the Nova API key workflow scripts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

from app.clients.interfaces import StoreAutomationClient
from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.secrets import mask_secret

logger = get_logger(__name__)


def build_nova_act_child_env(
    nova_api_key: str | None,
    source_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build child process env exactly as live workflow subprocess expects."""
    env = dict(source_env or os.environ)
    if nova_api_key:
        env["NOVA_API_KEY"] = nova_api_key
        env["NOVA_ACT_API_KEY"] = nova_api_key
    env["NOVA_ACT_LOG_LEVEL"] = "40"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


class NovaActClient(StoreAutomationClient):
    """Run the checked-in Nova Act scripts with a Nova API key."""

    def __init__(self) -> None:
        settings = get_settings()
        self.nova_api_key = settings.nova_api_key
        self.timeout_seconds = settings.nova_act_timeout_seconds
        self.repo_root = Path(__file__).resolve().parents[3]
        self.script_by_site = {
            "amazon": self.repo_root / "scripts" / "amazon_workflow.py",
            "jumia": self.repo_root / "scripts" / "jumia_workflow.py",
        }

    def run_store_workflow(self, site: str, interpreted_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a live workflow script and return extracted product dictionaries."""
        if not self.nova_api_key:
            raise RuntimeError("Set NOVA_API_KEY in backend/.env before running live Nova Act workflows.")

        script_path = self.script_by_site.get(site.lower())
        if not script_path or not script_path.exists():
            raise RuntimeError(f"No live Nova Act script is available for site '{site}'.")

        query = str(interpreted_request.get("query", "")).strip()
        if not query:
            raise RuntimeError("No user query was provided for live workflow execution.")

        command = [sys.executable, str(script_path), "--query", query]
        search_terms = interpreted_request.get("search_terms")
        if isinstance(search_terms, list):
            command.extend(["--search-terms-json", json.dumps(search_terms)])
        category = str(interpreted_request.get("category") or "").strip()
        if category:
            command.extend(["--category", category])
        budget_max = interpreted_request.get("budget_max")
        if budget_max is not None:
            command.extend(["--budget-max", str(budget_max)])
        budget_currency = str(interpreted_request.get("budget_currency") or "").strip()
        if budget_currency and site.lower() == "amazon":
            command.extend(["--budget-currency", budget_currency])
        max_results = interpreted_request.get("max_results")
        if max_results is not None:
            command.extend(["--max-results", str(max_results)])
        max_search_terms = interpreted_request.get("max_search_terms")
        if max_search_terms is not None:
            command.extend(["--max-search-terms", str(max_search_terms)])
        if site.lower() == "amazon":
            country = str(interpreted_request.get("user_location") or "Nigeria").strip()
            command.extend(["--country", country])

        env = build_nova_act_child_env(self.nova_api_key)

        try:
            site_key = site.lower().strip()
            effective_timeout = self.timeout_seconds
            if site_key == "jumia":
                # Jumia script is optimized for short deterministic extraction; clamp for faster failure.
                effective_timeout = min(effective_timeout, 120)
            logger.info(
                "NOVAPILOT_DEBUG nova_act_command site=%s script=%s timeout=%s command=%s",
                site,
                str(script_path),
                effective_timeout,
                command,
            )
            logger.info(
                "NOVAPILOT_DEBUG nova_act_parent_env site=%s settings_nova_api_key_present=%s masked_settings_nova_api_key=%s os_environ_has_nova_act_api_key=%s masked_nova_act_api_key=%s os_environ_has_nova_api_key=%s masked_nova_api_key=%s child_env_has_nova_act_api_key=%s masked_child_nova_act_api_key=%s child_env_has_nova_api_key=%s masked_child_nova_api_key=%s",
                site,
                bool(self.nova_api_key),
                mask_secret(self.nova_api_key),
                bool(os.environ.get("NOVA_ACT_API_KEY")),
                mask_secret(os.environ.get("NOVA_ACT_API_KEY")),
                bool(os.environ.get("NOVA_API_KEY")),
                mask_secret(os.environ.get("NOVA_API_KEY")),
                bool(env.get("NOVA_ACT_API_KEY")),
                mask_secret(env.get("NOVA_ACT_API_KEY")),
                bool(env.get("NOVA_API_KEY")),
                mask_secret(env.get("NOVA_API_KEY")),
            )
            completed = subprocess.run(
                command,
                cwd=str(self.repo_root),
                env=env,
                capture_output=True,
                text=False,
                timeout=effective_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"Nova Act script timed out for {site} after {effective_timeout}s.") from exc

        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        logger.info(
            "NOVAPILOT_DEBUG nova_act_completed site=%s returncode=%s stdout_snippet=%s stderr_snippet=%s",
            site,
            completed.returncode,
            stdout[:1000],
            stderr[:1000],
        )

        if completed.returncode != 0:
            message = stderr or stdout
            raise RuntimeError(message or f"Nova Act script failed for {site} with exit code {completed.returncode}.")

        payload = self._parse_json_payload(stdout, stderr)
        payload_products = payload.get("products")
        payload_count = len(payload_products) if isinstance(payload_products, list) else 0
        logger.info(
            "NOVAPILOT_DEBUG nova_act_payload site=%s product_count=%s payload=%s",
            site,
            payload_count,
            payload,
        )
        payload_error = self._extract_payload_error(payload)
        if payload_error:
            raise RuntimeError(payload_error)
        products = payload.get("products")
        if not isinstance(products, list):
            raise RuntimeError(f"Nova Act script for {site} did not return a valid products array.")
        live_failure = self._detect_live_failure(stderr) or self._detect_live_failure(stdout)
        if not products and live_failure:
            raise RuntimeError(live_failure)
        return [item for item in products if isinstance(item, dict)]

    def _parse_json_payload(self, stdout: str, stderr: str = "") -> Dict[str, Any]:
        text = stdout.strip()
        combined = "\n".join(part for part in [stdout.strip(), stderr.strip()] if part).strip()
        if not text and combined:
            text = combined
        if not text:
            raise RuntimeError("Nova Act script returned no output.")
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        for candidate in [text, combined]:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end == -1 or end <= start:
                continue
            try:
                payload = json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload

        snippet = text or combined
        raise RuntimeError(f"Nova Act script returned non-JSON output: {snippet[:400]}")

    def _extract_payload_error(self, payload: Dict[str, Any]) -> str | None:
        raw_error = payload.get("error")
        if not raw_error:
            return None
        text = str(raw_error).strip()
        if not text:
            return None
        return text

    def _detect_live_failure(self, text: str) -> str | None:
        if not text:
            return None
        lowered = text.lower()
        signal_map = {
            "failed to start the actuator": "Nova Act actuator could not start.",
            "api.nova.amazon.com": "Nova Act could not connect to api.nova.amazon.com.",
            "max retries exceeded": "Nova Act could not connect to api.nova.amazon.com.",
            "failed to establish a new connection": "Nova Act could not connect to api.nova.amazon.com.",
            "httpsconnectionpool": "Nova Act could not connect to api.nova.amazon.com.",
            "newconnectionerror": "Nova Act could not connect to api.nova.amazon.com.",
            "connectionerror": "Nova Act could not connect to api.nova.amazon.com.",
            "permissionerror": "Nova Act could not connect to api.nova.amazon.com.",
            "winerror 10013": "Nova Act could not connect to api.nova.amazon.com.",
            "timed out": "Nova Act request timed out.",
            "timeout": "Nova Act request timed out.",
            "unauthorized": "Nova Act authentication failed.",
            "forbidden": "Nova Act authentication failed.",
            "invalid api key": "Nova Act authentication failed.",
            "authentication": "Nova Act authentication failed.",
            "actactuationerror": "Nova Act actuator could not start.",
            "acttimeouterror": "Nova Act request timed out.",
            "actexceededmaxstepserror": "Nova Act exceeded maximum workflow steps.",
            "invalidcertificate": "Nova Act SSL certificate verification failed.",
            "targetclosederror": "Nova Act browser session closed unexpectedly.",
        }
        for signal, message in signal_map.items():
            if signal in lowered:
                return message

        if "traceback" in lowered and re.search(r"(nova[_ -]?act|httpsconnectionpool|newconnectionerror)", lowered):
            return self._first_meaningful_line(text)
        return None

    def _first_meaningful_line(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[:500]
        return text[:500]

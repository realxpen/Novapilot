"""Automation layer backed by live Nova Act workflows only."""

from typing import Any, Dict, List

from app.clients.interfaces import StoreAutomationClient
from app.clients.nova_act_client import NovaActClient
from app.schemas.response import InterpretedRequest


class AutomationService:
    """Run live store-level workflows and return extracted product payloads."""

    def __init__(
        self,
        nova_act_client: StoreAutomationClient | None = None,
        use_nova_act: bool = True,
        strict_live_mode: bool = True,
    ) -> None:
        self.nova_act_client = nova_act_client or NovaActClient()
        self.use_nova_act = use_nova_act
        self.strict_live_mode = strict_live_mode

    def run_site_workflow(
        self,
        site: str,
        interpreted: InterpretedRequest,
        query: str,
        user_location: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Execute a live workflow for one store and return raw product dictionaries."""
        if not self.use_nova_act:
            raise RuntimeError(
                "Mock data has been disabled. Set NOVAPILOT_USE_NOVA_ACT_AUTOMATION=true "
                "and configure a live Nova Act workflow for this store."
            )

        payload: Dict[str, Any] = interpreted.model_dump()
        payload["query"] = query
        if user_location:
            payload["user_location"] = user_location

        try:
            return self.nova_act_client.run_store_workflow(
                site=site,
                interpreted_request=payload,
            )
        except Exception as exc:  # noqa: BLE001 - live errors must surface directly now
            raise RuntimeError(f"Nova Act live workflow failed for {site}: {exc}") from exc

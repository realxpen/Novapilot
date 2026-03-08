"""AWS-ready placeholder client for Amazon Bedrock (Nova 2 Lite)."""

import os
import re
from typing import Any, Dict, List, Optional

from app.clients.interfaces import InterpretationClient, ReportGenerationClient
from app.schemas.product import Product
from app.schemas.response import InterpretedRequest


class BedrockClient(InterpretationClient, ReportGenerationClient):
    """Placeholder Bedrock adapter with env-driven model configuration.

    This class intentionally avoids real network calls in MVP mode.
    """

    def __init__(self) -> None:
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.interpret_model_id = os.getenv("NOVAPILOT_BEDROCK_INTERPRET_MODEL_ID", "amazon.nova-lite-v1:0")
        self.report_model_id = os.getenv("NOVAPILOT_BEDROCK_REPORT_MODEL_ID", "amazon.nova-lite-v1:0")

    def interpret_query(self, query: str, top_n: int) -> Optional[Dict[str, Any]]:
        """Return placeholder structured interpretation.

        TODO(AWS-NOVA2LITE-INTERPRET):
        - Build Bedrock runtime client using `self.aws_region`.
        - Invoke `self.interpret_model_id` with a strict JSON schema prompt.
        - Validate/parsing model JSON into this method's return shape.
        """
        lowered = query.lower()
        category = "laptop" if "laptop" in lowered else "electronics"
        use_case = "ui/ux design" if "design" in lowered or "ui/ux" in lowered else "general"
        budget_max = self._extract_budget(query)

        return {
            "category": category,
            "budget_currency": "NGN" if "\u20A6" in query or "naira" in lowered or "ngn" in lowered else "USD",
            "budget_max": budget_max,
            "use_case": use_case,
            "priority_specs": ["RAM", "CPU", "storage"] if category == "laptop" else ["price", "rating"],
            "top_n": top_n,
            "provider": "bedrock_placeholder",
            "region": self.aws_region,
            "model_id": self.interpret_model_id,
        }

    def generate_reasoning(
        self,
        query: str,
        interpreted: InterpretedRequest,
        best_pick: Optional[Product],
        alternatives: List[Product],
    ) -> Optional[str]:
        """Return placeholder narrative text.

        TODO(AWS-NOVA2LITE-REPORT):
        - Build Bedrock runtime client using `self.aws_region`.
        - Invoke `self.report_model_id` with best pick + alternatives context.
        - Return concise frontend-ready explanation.
        """
        if not best_pick:
            return (
                f"Bedrock placeholder ({self.report_model_id}) could not generate a recommendation "
                "because no ranked product is available."
            )

        return (
            f"Bedrock placeholder ({self.report_model_id}) suggests {best_pick.name} for "
            f"{interpreted.use_case} based on balanced price and specifications."
        )

    def _extract_budget(self, query: str) -> Optional[float]:
        patterns = [
            r"(?:under|below|less than)\s*(?:\u20A6|\$)?\s*([\d,]+(?:\.\d+)?)",
            r"(?:\u20A6|\$)\s*([\d,]+(?:\.\d+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, flags=re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    return None
        return None

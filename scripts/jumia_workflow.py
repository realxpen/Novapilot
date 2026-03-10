"""Nova Act workflow runner for Jumia product search and extraction.

Usage (PowerShell):
  $env:NOVA_API_KEY="your_nova_key"
  python scripts/jumia_workflow.py --query "Find laptops under NGN 800000 for UI/UX design"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from nova_act import NovaAct, workflow

NOVA_ACT_KEY = os.getenv("NOVA_ACT_API_KEY") or os.getenv("NOVA_API_KEY")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def build_prompt(query: str) -> str:
    return (
        "Open jumia.com.ng and search for this request: "
        f"'{query}'.\n"
        "Open relevant product detail pages and extract up to 8 products.\n"
        "Return JSON only with top-level key 'products', where each item has keys: "
        "title, price_text, currency, rating, specs, url, image.\n"
        "If a field is missing, use null."
    )


@workflow(
    workflow_definition_name="novapilot_search_jumia",
    model_id="nova-act-latest",
    nova_act_api_key=NOVA_ACT_KEY,
)
def run_jumia_workflow(query: str) -> Any:
    if not NOVA_ACT_KEY:
        raise RuntimeError("Set NOVA_ACT_API_KEY (or NOVA_API_KEY) before running this script.")

    with NovaAct(
        starting_page="https://www.jumia.com.ng/",
        nova_act_api_key=NOVA_ACT_KEY,
    ) as nova:
        prompt = build_prompt(query)
        return nova.act(prompt, ignore_screen_dims_check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NovaPilot Jumia workflow")
    parser.add_argument(
        "--query",
        default="Find laptops under NGN 800000 for UI/UX design",
        help="Shopping query to execute on Jumia",
    )
    args = parser.parse_args()

    result = run_jumia_workflow(args.query)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

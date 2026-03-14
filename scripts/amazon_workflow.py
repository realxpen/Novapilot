"""Nova Act workflow runner for Amazon product search and extraction.

Usage (PowerShell):
  $env:NOVA_API_KEY="your_nova_key"
  python scripts/amazon_workflow.py --query "Find laptops under NGN 800000 for UI/UX design"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import quote_plus
from typing import Any

from nova_act import NovaAct, workflow

NOVA_ACT_KEY = os.getenv("NOVA_ACT_API_KEY") or os.getenv("NOVA_API_KEY")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def build_schema(max_results: int) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["products"],
        "properties": {
            "products": {
                "type": "array",
                "maxItems": max(1, max_results),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "name",
                        "amount",
                        "currency_code",
                        "rating",
                        "details",
                        "product_url",
                        "image_url",
                    ],
                    "properties": {
                        "name": {"type": ["string", "null"]},
                        "amount": {"type": ["string", "number", "null"]},
                        "currency_code": {"type": ["string", "null"]},
                        "rating": {"type": ["string", "number", "null"]},
                        "details": {"type": ["string", "null"]},
                        "product_url": {"type": ["string", "null"]},
                        "image_url": {"type": ["string", "null"]},
                    },
                },
            }
        },
    }


def build_starting_page(query: str, search_terms: list[str]) -> str:
    first_term = next((term.strip() for term in search_terms if term.strip()), query.strip())
    if not first_term:
        return "https://www.amazon.com/"
    return f"https://www.amazon.com/s?k={quote_plus(first_term)}"


def build_prompt(
    query: str,
    country: str,
    category: str,
    search_terms: list[str],
    budget_max: float | None,
    max_results: int,
) -> str:
    trimmed_terms = [term for term in search_terms if term.strip()][:4]
    ordered_terms = ", ".join(f"'{term}'" for term in trimmed_terms)
    if not ordered_terms:
        ordered_terms = f"'{query}'"

    product_type = {
        "laptop": "laptop/computer",
        "tablet": "tablet/ipad",
        "smartphone": "phone/smartphone",
        "audio": "audio/headphone",
    }.get(category.lower(), "product")
    excluded = {
        "laptop": "accessories, laptop bags, laptop sleeves, laptop skins, stickers, books, courses, backpacks, decals, and any non-laptop result",
        "tablet": "tablet cases, keyboard cases, stylus-only listings, screen protectors, chargers, accessories, phone results, and any non-tablet result",
        "smartphone": "phone cases, chargers, screen protectors, earphones, replacement parts, accessories, and any non-phone result",
        "audio": "phone cases, speakers, microphones, cables, accessories, and any non-headphone result",
    }.get(category.lower(), "accessories and unrelated results")

    budget_guard = ""
    if budget_max is not None:
        budget_guard = (
            f" Only keep products priced at or below the budget cap of {budget_max:.0f}. "
            "Do not include over-budget products."
        )

    return (
        "You are already on Amazon search results for the first concrete product term.\n"
        f"Set delivery location/country to '{country}' before opening product pages if possible.\n"
        "Prefer listings and product pages that display local pricing in NGN when available.\n"
        "If NGN is not available, keep the original displayed currency code exactly as shown.\n"
        f"Use these search terms in order only when needed: {ordered_terms}.\n"
        "Stay only on Amazon search results and Amazon product detail pages.\n"
        "Do not inspect sponsored rows, carousels, ads, or unrelated widgets.\n"
        f"Ignore and skip {excluded}.\n"
        f"Collect up to {max_results} real {product_type} product detail pages only.\n"
        "Inspect only the first visible strong matching cards.\n"
        "Open the first clearly relevant product page immediately.\n"
        "If the current results are irrelevant, use the next search term in the Amazon search box.\n"
        "Use the raw user sentence only as a last fallback.\n"
        "Stop as soon as you have enough valid products."
        f"{budget_guard}\n"
        "Return only product detail page URLs, never search or category URLs.\n"
        "Ensure 'product_url' is an absolute https URL on amazon.*.\n"
        "Ensure 'image_url' is an absolute https image URL for that exact product.\n"
        "For each product, keep a short details summary from the page.\n"
        "Return only the structured response requested by the schema."
    )


@workflow(
    workflow_definition_name="novapilot_search_amazon",
    model_id="nova-act-latest",
    nova_act_api_key=NOVA_ACT_KEY,
)
def run_amazon_workflow(
    query: str,
    country: str = "Nigeria",
    category: str = "electronics",
    budget_max: float | None = None,
    max_results: int = 2,
    search_terms: list[str] | None = None,
) -> Any:
    if not NOVA_ACT_KEY:
        raise RuntimeError("Set NOVA_ACT_API_KEY (or NOVA_API_KEY) before running this script.")

    cleaned_terms = [term.strip() for term in (search_terms or [query]) if term.strip()]
    with NovaAct(
        starting_page=build_starting_page(query, cleaned_terms),
        nova_act_api_key=NOVA_ACT_KEY,
        ignore_https_errors=True,
    ) as nova:
        prompt = build_prompt(
            query,
            country,
            category,
            cleaned_terms or [query],
            budget_max,
            max_results,
        )
        result = nova.act_get(
            prompt,
            schema=build_schema(max_results),
            max_steps=20,
        )
        payload = result.parsed_response
        if not isinstance(payload, dict):
            raise RuntimeError("Nova Act did not return a structured response for Amazon.")
        return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NovaPilot Amazon workflow")
    parser.add_argument(
        "--query",
        default="Find laptops under NGN 800000 for UI/UX design",
        help="Shopping query to execute on Amazon",
    )
    parser.add_argument(
        "--country",
        default="Nigeria",
        help="Country/location to set on Amazon before searching",
    )
    parser.add_argument(
        "--search-terms-json",
        default="[]",
        help="JSON array of concrete search terms to try before the raw query",
    )
    parser.add_argument(
        "--category",
        default="electronics",
        help="Interpreted product category",
    )
    parser.add_argument(
        "--budget-max",
        type=float,
        default=None,
        help="Optional maximum budget",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=2,
        help="Maximum number of valid products to collect",
    )
    parser.add_argument(
        "--max-search-terms",
        type=int,
        default=3,
        help="Maximum number of concrete search terms to try",
    )
    args = parser.parse_args()

    try:
        search_terms = json.loads(args.search_terms_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid --search-terms-json payload.") from exc
    if not isinstance(search_terms, list):
        search_terms = []

    result = run_amazon_workflow(
        args.query,
        args.country,
        args.category,
        args.budget_max,
        args.max_results,
        [str(term).strip() for term in search_terms if str(term).strip()][: args.max_search_terms],
    )
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

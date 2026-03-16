"""Deterministic ShopInverse product extraction via Shopify collection feeds.

Usage (PowerShell):
  python scripts/shopinverse_workflow.py --query "Laptop for programming under NGN 900000"
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


SHOPINVERSE_BASE = "https://shopinverse.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

COLLECTIONS_BY_CATEGORY: dict[str, list[str]] = {
    "laptop": ["laptops"],
    "smartphone": ["phone-and-tablets"],
    "tablet": ["phone-and-tablets"],
    "audio": ["accessories", "smart-gadgets"],
    "electronics": ["laptops", "phone-and-tablets", "smart-gadgets", "accessories"],
}

GENERIC_SEARCH_STOPWORDS = {
    "best",
    "top",
    "good",
    "great",
    "budget",
    "under",
    "below",
    "less",
    "than",
    "around",
    "about",
    "for",
    "with",
    "without",
    "find",
    "need",
    "want",
    "looking",
    "buy",
}

DEDUPLICATION_STOPWORDS = {
    "black",
    "blue",
    "white",
    "silver",
    "gray",
    "grey",
    "gold",
    "green",
    "red",
    "purple",
    "new",
    "with",
    "for",
    "and",
    "the",
}


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for term in terms:
        normalized = " ".join(str(term).strip().lower().split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(str(term).strip())
    return ordered


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", html.unescape(value)).strip()
    return normalized or None


def _strip_html_tags(fragment: str | None) -> str:
    if not fragment:
        return ""
    no_tags = re.sub(r"<[^>]+>", " ", fragment)
    return _clean_text(no_tags) or ""


def _significant_tokens(*values: str | None) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        cleaned = re.sub(r"[^a-z0-9\s]", " ", value.lower())
        for token in cleaned.split():
            if len(token) <= 2 or token in GENERIC_SEARCH_STOPWORDS:
                continue
            if token in seen:
                continue
            seen.add(token)
            tokens.append(token)
    return tokens


def _parse_price_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    matches = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    if not matches:
        return None
    try:
        return float(matches[0].replace(",", ""))
    except ValueError:
        return None


def _format_ngn(value: float | None) -> str | None:
    if value is None:
        return None
    return f"NGN {value:,.0f}"


def _normalize_url(value: str | None) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.startswith("//"):
        return f"https:{text}"
    if text.startswith("/"):
        return urljoin(SHOPINVERSE_BASE, text)
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return None


def _normalize_product_url(handle: str | None) -> str | None:
    cleaned_handle = _clean_text(handle)
    if not cleaned_handle:
        return None
    return f"{SHOPINVERSE_BASE}/products/{cleaned_handle}"


def _normalize_image_url(value: str | None) -> str | None:
    normalized = _normalize_url(value)
    if not normalized:
        return None
    lowered = normalized.lower()
    if lowered.startswith("data:"):
        return None
    if "shopinverse.com" not in lowered and "shopify.com" not in lowered:
        return None
    return normalized


def _http_get_json(url: str, timeout: int = 15) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/javascript,*/*;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    payload = json.loads(raw.decode("utf-8", errors="replace"))
    return payload if isinstance(payload, dict) else {}


def _candidate_group_key(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", title)
    tokens = [token for token in cleaned.split() if token and token not in DEDUPLICATION_STOPWORDS]
    if tokens:
        return " ".join(tokens[:10])
    return str(item.get("url") or "").strip().lower()


def _is_relevant_for_category(text: str, category: str) -> bool:
    lowered = text.lower()
    if not lowered:
        return False

    blocked = {
        "laptop": ("bag", "sleeve", "skin", "sticker", "adapter", "battery"),
        "smartphone": ("case", "cover", "screen protector", "charger", "replacement", "battery"),
        "tablet": ("case", "cover", "screen protector", "charger", "keyboard case", "stylus only"),
        "audio": ("case", "cover", "cable", "adapter"),
    }
    if any(term in lowered for term in blocked.get(category.lower(), ())):
        return False

    expected = {
        "laptop": (
            "laptop",
            "notebook",
            "thinkpad",
            "elitebook",
            "latitude",
            "inspiron",
            "ideapad",
            "macbook",
            "probook",
        ),
        "smartphone": (
            "phone",
            "smartphone",
            "iphone",
            "galaxy",
            "pixel",
            "redmi",
            "xiaomi",
            "infinix",
            "tecno",
            "oppo",
            "vivo",
        ),
        "tablet": ("tablet", "ipad", "tab ", "galaxy tab", "redmi pad", "xiaomi pad"),
        "audio": ("headphone", "earbud", "earphone", "buds", "airpods"),
    }
    allowed = expected.get(category.lower())
    if not allowed:
        return True
    return any(term in lowered for term in allowed)


def _build_specs_blob(product: dict[str, Any]) -> str:
    body = _strip_html_tags(str(product.get("body_html") or ""))
    vendor = _clean_text(str(product.get("vendor") or "")) or ""
    product_type = _clean_text(str(product.get("product_type") or "")) or ""
    tags = product.get("tags")
    if isinstance(tags, list):
        tags_text = " ".join(str(tag).strip() for tag in tags if str(tag).strip())
    else:
        tags_text = str(tags or "")
    variant_titles = " ".join(
        str(variant.get("title") or "").strip()
        for variant in product.get("variants", [])
        if isinstance(variant, dict)
    )
    return " ".join(part for part in [body, vendor, product_type, tags_text, variant_titles] if part).strip()


def _candidate_score(
    *,
    title: str,
    specs: str,
    price: float | None,
    query: str,
    search_terms: list[str],
    category: str,
    budget_max: float | None,
) -> float:
    text = f"{title} {specs}".lower()
    score = 0.0

    tokens = _significant_tokens(query, *search_terms)
    match_count = sum(1 for token in tokens if token in text)
    score += min(match_count, 8) * 1.4

    if category.lower() == "laptop":
        if "16gb" in text:
            score += 1.5
        elif "8gb" in text:
            score += 0.8
        if "512gb" in text or "512 gb" in text:
            score += 1.2
        if any(token in text for token in ["core i7", "core i5", "ryzen 7", "ryzen 5"]):
            score += 1.1
        if "ssd" in text:
            score += 0.8
    elif category.lower() in {"smartphone", "tablet"}:
        if any(token in text for token in ["8gb", "128gb", "256gb"]):
            score += 1.0
        if "5g" in text:
            score += 0.6

    if price is not None and budget_max is not None and budget_max > 0:
        if price <= budget_max:
            closeness = 1.0 - abs(budget_max - price) / budget_max
            score += max(0.0, closeness) * 1.6
        else:
            score -= min(3.5, ((price - budget_max) / budget_max) * 10.0)

    return round(score, 3)


def _collection_handles_for_category(category: str) -> list[str]:
    return COLLECTIONS_BY_CATEGORY.get(category.lower(), COLLECTIONS_BY_CATEGORY["electronics"])


def _fetch_collection_products(handle: str, page: int, limit: int = 100) -> list[dict[str, Any]]:
    url = f"{SHOPINVERSE_BASE}/collections/{handle}/products.json?limit={limit}&page={page}"
    payload = _http_get_json(url)
    products = payload.get("products")
    if not isinstance(products, list):
        return []
    return [product for product in products if isinstance(product, dict)]


def _extract_candidate(
    product: dict[str, Any],
    *,
    query: str,
    search_terms: list[str],
    category: str,
    budget_max: float | None,
) -> dict[str, Any] | None:
    title = _clean_text(str(product.get("title") or "")) or ""
    specs = _build_specs_blob(product)
    text_blob = f"{title} {specs}".strip()
    if not _is_relevant_for_category(text_blob, category):
        return None

    variants = product.get("variants", [])
    prices = [
        _parse_price_value(variant.get("price"))
        for variant in variants
        if isinstance(variant, dict)
    ]
    price_candidates = [price for price in prices if price is not None and price > 0]
    if not price_candidates:
        return None
    price = min(price_candidates)
    if budget_max is not None and price > budget_max:
        return None

    handle = _clean_text(str(product.get("handle") or "")) or ""
    url = _normalize_product_url(handle)
    if not url:
        return None

    image_source = None
    if isinstance(product.get("image"), dict):
        image_source = product["image"].get("src")
    if not image_source:
        images = product.get("images")
        if isinstance(images, list) and images:
            first_image = images[0]
            if isinstance(first_image, dict):
                image_source = first_image.get("src")
    image = _normalize_image_url(image_source)

    return {
        "title": title,
        "specs": specs,
        "price_text": _format_ngn(price),
        "currency": "NGN",
        "url": url,
        "image": image,
        "rating": None,
        "_candidate_score": _candidate_score(
            title=title,
            specs=specs,
            price=price,
            query=query,
            search_terms=search_terms,
            category=category,
            budget_max=budget_max,
        ),
    }


def run_shopinverse_workflow(
    query: str,
    country: str = "Nigeria",
    category: str = "electronics",
    budget_max: float | None = None,
    budget_currency: str | None = "NGN",
    max_results: int = 5,
    search_terms: list[str] | None = None,
    max_search_terms: int = 4,
) -> dict[str, Any]:
    del country, budget_currency

    cleaned_terms = _dedupe_terms(
        [query.strip(), *[term.strip() for term in (search_terms or [query]) if term.strip()]]
    )[: max(1, min(max_search_terms, 8))]
    handles = _collection_handles_for_category(category)
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    errors: list[str] = []
    debug_collections: list[dict[str, Any]] = []

    for handle in handles:
        total_fetched = 0
        for page in range(1, 3):
            try:
                products = _fetch_collection_products(handle, page)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{handle} page {page}: {exc}")
                break
            if not products:
                break
            total_fetched += len(products)
            for product in products:
                candidate = _extract_candidate(
                    product,
                    query=query,
                    search_terms=cleaned_terms,
                    category=category,
                    budget_max=budget_max,
                )
                if not candidate:
                    continue
                url_key = str(candidate.get("url") or "").strip().lower()
                if not url_key or url_key in seen_urls:
                    continue
                seen_urls.add(url_key)
                candidates.append(candidate)
        debug_collections.append({"handle": handle, "fetched_products": total_fetched})

    ranked = sorted(
        candidates,
        key=lambda item: float(item.get("_candidate_score", 0.0)),
        reverse=True,
    )

    selected: list[dict[str, Any]] = []
    seen_groups: set[str] = set()
    for item in ranked:
        group_key = _candidate_group_key(item)
        if group_key in seen_groups:
            continue
        seen_groups.add(group_key)
        selected.append({key: value for key, value in item.items() if not str(key).startswith("_")})
        if len(selected) >= max(1, min(max_results, 5)):
            break

    return {
        "products": selected,
        "errors": errors,
        "debug": {
            "query": query,
            "category": category,
            "budget_max": budget_max,
            "search_terms": cleaned_terms,
            "collections": debug_collections,
            "candidate_count": len(candidates),
            "selected_count": len(selected),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ShopInverse workflow")
    parser.add_argument(
        "--query",
        default="Laptop for programming under NGN 900000",
        help="Shopping query to execute on ShopInverse",
    )
    parser.add_argument(
        "--country",
        default="Nigeria",
        help="User market context",
    )
    parser.add_argument(
        "--search-terms-json",
        default="[]",
        help="JSON array of concrete search terms to score against",
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
        "--budget-currency",
        default="NGN",
        help="Currency code for the budget max",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of valid products to collect",
    )
    parser.add_argument(
        "--max-search-terms",
        type=int,
        default=4,
        help="Maximum number of search terms to score against",
    )
    args = parser.parse_args()

    try:
        search_terms = json.loads(args.search_terms_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid --search-terms-json payload.") from exc
    if not isinstance(search_terms, list):
        search_terms = []

    result = run_shopinverse_workflow(
        query=args.query,
        country=args.country,
        category=args.category,
        budget_max=args.budget_max,
        budget_currency=args.budget_currency,
        max_results=args.max_results,
        search_terms=[str(term).strip() for term in search_terms if str(term).strip()],
        max_search_terms=args.max_search_terms,
    )
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

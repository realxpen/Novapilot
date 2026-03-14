"""Nova Act workflow runner for Jumia product search and extraction.

Usage (PowerShell):
  $env:NOVA_API_KEY="your_nova_key"
  python scripts/jumia_workflow.py --query "Find laptops under NGN 800000 for UI/UX design"
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import sys
import time
import zlib
from datetime import datetime, timezone
from urllib.parse import quote_plus, urljoin
from urllib.request import Request, urlopen
from typing import Any

from nova_act import NovaAct

NOVA_ACT_KEY = os.getenv("NOVA_ACT_API_KEY") or os.getenv("NOVA_API_KEY")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


JUMIA_BASE = "https://www.jumia.com.ng"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _timing_log(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    print(f"JUMIA_TIMING {json.dumps(payload, ensure_ascii=False, default=str)}", file=sys.stderr)


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


def normalize_search_terms(category: str, query: str, terms: list[str]) -> list[str]:
    cleaned = [str(term).strip() for term in terms if str(term).strip()]
    if category.lower() != "laptop":
        return cleaned or [query]

    laptop_fallback_terms = [
        "Dell Latitude 7490 16GB 512GB laptop",
        "HP EliteBook 840 G6 16GB 512GB laptop",
        "Dell Inspiron 15 Core i5 16GB 512GB laptop",
        "Lenovo IdeaPad 3 Core i5 16GB 512GB laptop",
        "laptop Core i5 16GB 512GB",
    ]

    non_thinkpad = [term for term in cleaned if "thinkpad" not in term.lower()]
    thinkpad = [term for term in cleaned if "thinkpad" in term.lower()]

    if not non_thinkpad:
        return laptop_fallback_terms

    # Keep user terms first, but push thinkpad to the end and always include strong fallback terms.
    return _dedupe_terms(non_thinkpad + laptop_fallback_terms + thinkpad)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", html.unescape(value)).strip()
    return normalized or None


def _strip_html_tags(fragment: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", fragment)
    return _clean_text(no_tags) or ""


def _parse_price_value(price_text: str | None) -> float | None:
    if not price_text:
        return None
    # Capture numeric chunks instead of concatenating all digits from price + discount + old price.
    matches = re.findall(r"\d[\d,]*(?:\.\d+)?", price_text)
    if not matches:
        return None

    parsed_values: list[float] = []
    for token in matches:
        try:
            parsed_values.append(float(token.replace(",", "")))
        except ValueError:
            continue

    if not parsed_values:
        return None

    # Prefer the first realistic monetary value in the string.
    for value in parsed_values:
        if value >= 100:
            return value
    return parsed_values[0]


def _price_to_currency(price_text: str | None) -> str | None:
    if not price_text:
        return None
    upper = price_text.upper()
    if "$" in price_text or "USD" in upper:
        return "USD"
    if "\u20A6" in price_text or "â‚¦" in price_text or "NGN" in upper or "NAIRA" in upper:
        return "NGN"
    if re.search(r"\bN\s*[\d,]", upper):
        return "NGN"
    if re.search(r"\d", price_text):
        return "NGN"
    return None


def _normalize_jumia_url(value: str | None) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.startswith("//"):
        return f"https:{text}"
    if text.startswith("/"):
        return urljoin(JUMIA_BASE, text)
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return None


def _is_valid_jumia_product_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower().strip()
    if "jumia.com.ng" not in lowered:
        return False
    if "/catalog/?" in lowered or "catalog/?q=" in lowered:
        return False
    if lowered in {"https://www.jumia.com.ng", "https://www.jumia.com.ng/"}:
        return False
    return ".html" in lowered


def _title_from_jumia_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        slug = url.split("/")[-1].split(".html")[0]
    except Exception:  # noqa: BLE001
        return None
    slug = slug.replace("-", " ")
    cleaned = _clean_text(slug)
    return cleaned


def _is_relevant_for_category(title: str | None, category: str) -> bool:
    text = (title or "").lower()
    if not text:
        return False

    blocked = {
        "laptop": ("bag", "sleeve", "skin", "sticker", "backpack", "course", "book"),
        "smartphone": (
            "case",
            "cover",
            "charger",
            "screen protector",
            "earphone",
            "tempered glass",
            "power bank",
        ),
        "tablet": ("case", "cover", "screen protector", "keyboard case", "stylus only"),
        "audio": ("case", "cover", "speaker", "microphone", "cable"),
    }
    if any(term in text for term in blocked.get(category.lower(), ())):
        return False

    expected = {
        "laptop": (
            "laptop",
            "notebook",
            "elitebook",
            "latitude",
            "inspiron",
            "ideapad",
            "probook",
            "macbook",
        ),
        "smartphone": (
            "phone",
            "smartphone",
            "galaxy",
            "iphone",
            "pixel",
            "redmi",
            "xiaomi",
            "infinix",
            "tecno",
            "oppo",
            "vivo",
            "realme",
        ),
        "tablet": ("tablet", "ipad", "tab ", "galaxy tab", "pad "),
        "audio": ("headphone", "earbud", "earphone", "buds", "wh-"),
    }
    allowed = expected.get(category.lower())
    if not allowed:
        return True
    return any(term in text for term in allowed)


def _normalize_product(item: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text(str(item.get("title") or "")) or None
    price_text = _clean_text(str(item.get("price_text") or "")) or None
    currency = _clean_text(str(item.get("currency") or "")) or _price_to_currency(price_text)
    rating_text = _clean_text(str(item.get("rating_text") or "")) or None
    specs = _clean_text(str(item.get("specs") or "")) or None
    url = _normalize_jumia_url(item.get("url"))
    if not title:
        title = _title_from_jumia_url(url)
    image = _normalize_jumia_url(item.get("image"))
    if image and "jumia" not in image.lower() and "jumia.is" not in image.lower():
        image = None
    return {
        "title": title,
        "price_text": price_text,
        "currency": currency,
        "rating_text": rating_text,
        "specs": specs,
        "url": url,
        "image": image,
    }


def _http_get(url: str, timeout: int = 25) -> str:
    started_at = datetime.now(timezone.utc).isoformat()
    request_start = time.monotonic()
    _timing_log(
        "http_request_start",
        url=url,
        timeout_s=timeout,
        started_at=started_at,
    )

    try:
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-NG,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, identity",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status_code = getattr(response, "status", None)
            content_type = response.headers.get("Content-Type", "")
            content_encoding = (response.headers.get("Content-Encoding", "") or "").lower().strip()
    except Exception as exc:  # noqa: BLE001
        _timing_log(
            "http_request_end",
            url=url,
            timeout_s=timeout,
            started_at=started_at,
            ok=False,
            duration_ms=round((time.monotonic() - request_start) * 1000, 1),
            exception_type=f"{exc.__class__.__module__}.{exc.__class__.__name__}",
            exception_message=str(exc),
        )
        raise

    _timing_log(
        "http_request_end",
        url=url,
        timeout_s=timeout,
        started_at=started_at,
        ok=True,
        duration_ms=round((time.monotonic() - request_start) * 1000, 1),
        status_code=status_code,
        content_type=content_type,
        content_encoding=content_encoding,
    )

    if content_encoding == "gzip":
        try:
            raw = gzip.decompress(raw)
        except Exception:  # noqa: BLE001
            pass
    elif content_encoding == "deflate":
        try:
            raw = zlib.decompress(raw)
        except Exception:  # noqa: BLE001
            try:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:  # noqa: BLE001
                pass

    match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    charset = match.group(1) if match else "utf-8"
    return raw.decode(charset, errors="replace")


def _extract_card_from_block(url: str | None, block: str) -> dict[str, Any] | None:
    if not _is_valid_jumia_product_url(url):
        return None

    title_match = re.search(
        r"<h3[^>]*class=[\"'][^\"']*\bname\b[^\"']*[\"'][^>]*>(.*?)</h3>",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    title = _strip_html_tags(title_match.group(1)) if title_match else None

    price_match = re.search(
        r"<div[^>]*class=[\"'][^\"']*\bprc\b[^\"']*[\"'][^>]*>(.*?)</div>",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    price_text = _strip_html_tags(price_match.group(1)) if price_match else None

    rating_match = re.search(r"(\d(?:\.\d)?)\s*out of 5", block, re.IGNORECASE)
    rating_text = rating_match.group(1) if rating_match else None

    image_match = re.search(r'data-src="([^"]+)"', block, re.IGNORECASE)
    if not image_match:
        image_match = re.search(r'src="([^"]+)"', block, re.IGNORECASE)
    image_url = _normalize_jumia_url(image_match.group(1)) if image_match else None

    if not title:
        alt_match = re.search(r'alt="([^"]+)"', block, re.IGNORECASE)
        if alt_match:
            title = _clean_text(alt_match.group(1))
    if not title:
        title = _title_from_jumia_url(url)

    if image_url and image_url.startswith("data:"):
        image_url = None

    return {
        "title": title,
        "price_text": price_text,
        "currency": _price_to_currency(price_text),
        "rating_text": rating_text,
        "specs": title,
        "url": url,
        "image": image_url,
    }


def _parse_search_cards(html_text: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    # Primary parser: product anchors on search grid.
    core_pattern = re.compile(
        r"<a[^>]*href=[\"']([^\"']+?\.html(?:\?[^\"']*)?)[\"'][^>]*class=[\"'][^\"']*\bcore\b[^\"']*[\"'][^>]*>(.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    for match in core_pattern.finditer(html_text):
        url = _normalize_jumia_url(match.group(1))
        if not _is_valid_jumia_product_url(url):
            continue
        key = str(url).strip().lower()
        if key in seen_urls:
            continue
        card = _extract_card_from_block(url, match.group(2))
        if not card:
            continue
        cards.append(card)
        seen_urls.add(key)

    # Fallback parser: full product article blocks.
    if cards:
        return cards

    article_pattern = re.compile(
        r"<article[^>]*class=[\"'][^\"']*prd[^\"']*[\"'][^>]*>.*?</article>",
        re.IGNORECASE | re.DOTALL,
    )
    for block in article_pattern.findall(html_text):
        href_match = re.search(r'href=[\"\']([^\"\']+?\.html(?:\?[^\"\']*)?)[\"\']', block, re.IGNORECASE)
        if not href_match:
            continue
        url = _normalize_jumia_url(href_match.group(1))
        key = str(url or "").strip().lower()
        if not key or key in seen_urls:
            continue
        card = _extract_card_from_block(url, block)
        if not card:
            continue
        cards.append(card)
        seen_urls.add(key)

    return cards


def _parse_search_cards_loose(html_text: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    link_pattern = re.compile(r"<a([^>]+)href=[\"']([^\"']+?\.html(?:\?[^\"']*)?)[\"']([^>]*)>", re.IGNORECASE)

    for match in link_pattern.finditer(html_text):
        attrs = f"{match.group(1)} {match.group(3)}"
        url = _normalize_jumia_url(match.group(2))
        if not _is_valid_jumia_product_url(url):
            continue
        lowered_attrs = attrs.lower()
        if "catalog/?" in lowered_attrs:
            continue
        key = str(url).strip().lower()
        if key in seen_urls:
            continue

        title = None
        name_match = re.search(r'data-name=[\"\']([^\"\']+)[\"\']', attrs, re.IGNORECASE)
        if name_match:
            title = _clean_text(name_match.group(1))
        if not title:
            title = _title_from_jumia_url(url)

        price_text = None
        price_match = re.search(r'data-price=[\"\']([^\"\']+)[\"\']', attrs, re.IGNORECASE)
        if price_match:
            raw_price = _clean_text(price_match.group(1))
            if raw_price:
                price_text = f"NGN {raw_price}"

        cards.append(
            {
                "title": title,
                "price_text": price_text,
                "currency": _price_to_currency(price_text),
                "rating_text": None,
                "specs": title,
                "url": url,
                "image": None,
            }
        )
        seen_urls.add(key)
    return cards


def _extract_meta_content(html_text: str, key: str) -> str | None:
    pattern = re.compile(
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    match = pattern.search(html_text)
    return _clean_text(match.group(1)) if match else None


def _extract_key_features(html_text: str) -> str | None:
    section_pattern = re.compile(
        r"Key Features.*?<ul[^>]*>(.*?)</ul>",
        re.IGNORECASE | re.DOTALL,
    )
    section = section_pattern.search(html_text)
    if not section:
        return None

    features: list[str] = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", section.group(1), re.IGNORECASE | re.DOTALL):
        text = _strip_html_tags(li)
        if text and len(text) >= 3:
            features.append(text)
        if len(features) == 3:
            break
    if not features:
        return None
    return "; ".join(features)


def _fetch_product_page_snapshot(url: str, timeout: int = 8) -> dict[str, Any]:
    try:
        html_text = _http_get(url, timeout=timeout)
    except Exception:  # noqa: BLE001
        return {}

    title = _extract_meta_content(html_text, "og:title")
    image = _normalize_jumia_url(_extract_meta_content(html_text, "og:image"))
    if image and "jumia" not in image.lower() and "jumia.is" not in image.lower():
        image = None
    price_amount = _extract_meta_content(html_text, "product:price:amount")
    currency = _extract_meta_content(html_text, "product:price:currency")
    price_text = None
    if price_amount:
        amount = re.sub(r"[^\d.,]", "", price_amount)
        price_text = f"NGN {amount}" if amount else None
    rating_text = None
    rating_match = re.search(r"(\d(?:\.\d)?)\s*out of 5", html_text, re.IGNORECASE)
    if rating_match:
        rating_text = rating_match.group(1)
    specs = _extract_key_features(html_text)
    return {
        "title": title,
        "price_text": price_text,
        "currency": currency,
        "rating_text": rating_text,
        "specs": specs,
        "url": url,
        "image": image,
    }


def fallback_extract_from_search(
    query: str,
    category: str,
    budget_max: float | None,
    max_results: int,
    search_terms: list[str],
    deadline_ts: float | None = None,
    *,
    max_terms: int = 2,
    max_cards_per_term: int = 3,
    max_snapshot_fetches: int = 2,
    search_timeout: int = 4,
    snapshot_timeout: int = 3,
    phase: str = "fallback",
) -> dict[str, Any]:
    phase_start = time.monotonic()
    target_count = max(1, max_results)
    terms = [term for term in search_terms if term.strip()] or [query]
    collected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    errors: list[str] = []
    search_pages_loaded = 0
    snapshot_fetches = 0

    _timing_log(
        "fallback_extract_start",
        phase=phase,
        target_count=target_count,
        max_terms=max_terms,
        max_cards_per_term=max_cards_per_term,
        max_snapshot_fetches=max_snapshot_fetches,
        search_timeout_s=search_timeout,
        snapshot_timeout_s=snapshot_timeout,
    )

    for term in terms[:max_terms]:
        if deadline_ts is not None and time.monotonic() >= deadline_ts:
            break
        if len(collected) >= target_count:
            break
        search_url = f"{JUMIA_BASE}/catalog/?q={quote_plus(term)}"
        term_start = time.monotonic()
        search_start = time.monotonic()
        try:
            page = _http_get(search_url, timeout=search_timeout)
            search_pages_loaded += 1
        except Exception as exc:  # noqa: BLE001
            duration_ms = round((time.monotonic() - search_start) * 1000, 1)
            error_text = str(exc)
            _timing_log(
                "search_page_fetch",
                phase=phase,
                term=term,
                url=search_url,
                ok=False,
                duration_ms=duration_ms,
                error=error_text,
            )
            errors.append(f"Search request for term '{term}' failed: {error_text}")
            continue
        duration_ms = round((time.monotonic() - search_start) * 1000, 1)
        _timing_log(
            "search_page_fetch",
            phase=phase,
            term=term,
            url=search_url,
            ok=True,
            duration_ms=duration_ms,
        )
        cards = _parse_search_cards(page)
        if len(cards) < 2:
            loose_cards = _parse_search_cards_loose(page)
            known = {str(card.get("url") or "").strip().lower() for card in cards}
            cards.extend(
                card for card in loose_cards if str(card.get("url") or "").strip().lower() not in known
            )
        _timing_log(
            "search_cards_parsed",
            phase=phase,
            term=term,
            card_count=len(cards),
        )
        inspected_candidates = 0
        for card in cards:
            if deadline_ts is not None and time.monotonic() >= deadline_ts:
                break
            if inspected_candidates >= max_cards_per_term:
                break
            if len(collected) >= target_count:
                break
            normalized_card = _normalize_product(card)
            normalize_start = time.monotonic()
            url = normalized_card.get("url")
            title = normalized_card.get("title")
            reason = None
            if not _is_valid_jumia_product_url(url):
                reason = "invalid_product_url"
            elif url in seen_urls:
                reason = "duplicate_url"
            elif not _is_relevant_for_category(title, category):
                reason = "category_mismatch"

            if reason:
                _timing_log(
                    "product_normalization",
                    phase=phase,
                    term=term,
                    accepted=False,
                    reason=reason,
                    duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                    title=title,
                    url=url,
                )
                continue
            inspected_candidates += 1
            merged = dict(normalized_card)
            merged_price = _parse_price_value(merged.get("price_text"))

            should_fetch_snapshot = merged_price is None and snapshot_fetches < max_snapshot_fetches

            if should_fetch_snapshot:
                snap_start = time.monotonic()
                snapshot = _normalize_product(_fetch_product_page_snapshot(url, timeout=snapshot_timeout))
                snapshot_fetches += 1
                _timing_log(
                    "product_snapshot_fetch",
                    phase=phase,
                    term=term,
                    ok=bool(snapshot),
                    duration_ms=round((time.monotonic() - snap_start) * 1000, 1),
                    url=url,
                    snapshot_fetches=snapshot_fetches,
                )
            else:
                snapshot = {}

            merged = {
                "title": snapshot.get("title") or normalized_card.get("title"),
                "price_text": snapshot.get("price_text") or normalized_card.get("price_text"),
                "currency": snapshot.get("currency") or normalized_card.get("currency"),
                "rating_text": snapshot.get("rating_text") or normalized_card.get("rating_text"),
                "specs": snapshot.get("specs") or normalized_card.get("specs"),
                "url": url,
                "image": snapshot.get("image") or normalized_card.get("image"),
            }
            if not _is_relevant_for_category(merged.get("title"), category):
                _timing_log(
                    "product_normalization",
                    phase=phase,
                    term=term,
                    accepted=False,
                    reason="category_mismatch_after_snapshot",
                    duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                    title=merged.get("title"),
                    url=url,
                )
                continue

            merged_price = _parse_price_value(merged.get("price_text"))
            if budget_max is not None and (merged_price is None or merged_price > budget_max):
                _timing_log(
                    "product_normalization",
                    phase=phase,
                    term=term,
                    accepted=False,
                    reason="over_budget_or_missing_price",
                    duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                    title=merged.get("title"),
                    url=url,
                    parsed_price=merged_price,
                )
                continue

            seen_urls.add(url)
            collected.append(merged)
            _timing_log(
                "product_normalization",
                phase=phase,
                term=term,
                accepted=True,
                reason="accepted",
                duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                title=merged.get("title"),
                url=url,
                parsed_price=merged_price,
                collected_count=len(collected),
            )
            if len(collected) >= target_count:
                break
        _timing_log(
            "search_term_end",
            phase=phase,
            term=term,
            duration_ms=round((time.monotonic() - term_start) * 1000, 1),
            inspected_candidates=inspected_candidates,
            collected_count=len(collected),
        )

    result = {
        "products": collected,
        "errors": errors,
        "search_pages_loaded": search_pages_loaded,
        "snapshot_fetches": snapshot_fetches,
    }
    _timing_log(
        "fallback_extract_end",
        phase=phase,
        duration_ms=round((time.monotonic() - phase_start) * 1000, 1),
        collected_count=len(collected),
        errors_count=len(errors),
        search_pages_loaded=search_pages_loaded,
        snapshot_fetches=snapshot_fetches,
    )
    return result


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
                        "title",
                        "price_text",
                        "currency",
                        "url",
                    ],
                    "properties": {
                        "title": {"type": ["string", "null"]},
                        "price_text": {"type": ["string", "null"]},
                        "currency": {"type": ["string", "null"]},
                        "rating_text": {"type": ["string", "null"]},
                        "specs": {"type": ["string", "null"]},
                        "url": {"type": ["string", "null"]},
                        "image": {"type": ["string", "null"]},
                    },
                },
            }
        },
    }


def build_starting_page(query: str, search_terms: list[str]) -> str:
    first_term = next((term.strip() for term in search_terms if term.strip()), query.strip())
    if not first_term:
        return f"{JUMIA_BASE}/"
    return f"{JUMIA_BASE}/catalog/?q={quote_plus(first_term)}"


def build_prompt(
    term: str,
    category: str,
    budget_max: float | None,
) -> str:
    product_type = {
        "laptop": "laptop",
        "tablet": "tablet",
        "smartphone": "phone",
        "audio": "headphone",
    }.get(category.lower(), "product")
    budget_guard = f"Price must be <= {budget_max:.0f}." if budget_max is not None else ""
    return (
        f"You are on Jumia results for '{term}'. "
        f"Find one relevant {product_type} card near the top. "
        "Open only one product detail page. "
        f"{budget_guard} "
        "Return one product or an empty array. "
        "Use absolute https jumia.com.ng product URL. "
        "Do not browse other pages or run more searches. "
        "Return only schema JSON."
    )


def run_jumia_workflow(
    query: str,
    category: str = "electronics",
    budget_max: float | None = None,
    max_results: int = 2,
    search_terms: list[str] | None = None,
) -> Any:
    workflow_start = time.monotonic()
    hard_deadline = workflow_start + 55
    cleaned_terms = normalize_search_terms(category, query, search_terms or [query])
    target_count = max(1, min(max_results, 3))
    quick_target_count = min(target_count, 2)
    collected: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    workflow_errors: list[str] = []
    search_pages_loaded = 0
    live_failure_error: str | None = None

    _timing_log(
        "workflow_start",
        category=category,
        budget_max=budget_max,
        target_count=target_count,
        quick_target_count=quick_target_count,
        deadline_seconds=55,
        search_terms=cleaned_terms,
        nova_act_enabled=bool(NOVA_ACT_KEY),
    )

    def _finish(payload: dict[str, Any], reason: str) -> dict[str, Any]:
        _timing_log(
            "workflow_end",
            reason=reason,
            duration_ms=round((time.monotonic() - workflow_start) * 1000, 1),
            collected_count=len(payload.get("products", [])),
            search_pages_loaded=search_pages_loaded,
            errors_count=len(workflow_errors),
        )
        return payload

    def _add_products(items: Any) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            normalize_start = time.monotonic()
            if not isinstance(item, dict):
                _timing_log("act_product_normalization", accepted=False, reason="not_dict")
                continue
            normalized = _normalize_product(item)
            title = normalized.get("title")
            url = normalized.get("url")
            if not _is_valid_jumia_product_url(url):
                _timing_log(
                    "act_product_normalization",
                    accepted=False,
                    reason="invalid_product_url",
                    duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                    title=title,
                    url=url,
                )
                continue
            if not _is_relevant_for_category(title, category):
                _timing_log(
                    "act_product_normalization",
                    accepted=False,
                    reason="category_mismatch",
                    duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                    title=title,
                    url=url,
                )
                continue
            price_value = _parse_price_value(normalized.get("price_text"))
            if budget_max is not None and (price_value is None or price_value > budget_max):
                _timing_log(
                    "act_product_normalization",
                    accepted=False,
                    reason="over_budget_or_missing_price",
                    duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                    title=title,
                    url=url,
                    parsed_price=price_value,
                )
                continue
            key = str(url).strip().lower() or str(title or "").strip().lower()
            if not key or key in seen_keys:
                _timing_log(
                    "act_product_normalization",
                    accepted=False,
                    reason="duplicate_or_empty_key",
                    duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                    title=title,
                    url=url,
                )
                continue
            seen_keys.add(key)
            collected.append(normalized)
            _timing_log(
                "act_product_normalization",
                accepted=True,
                reason="accepted",
                duration_ms=round((time.monotonic() - normalize_start) * 1000, 1),
                title=title,
                url=url,
                collected_count=len(collected),
            )
            if len(collected) >= target_count:
                return

    # 1) Deterministic extraction first: return search-card products directly when valid.
    first_phase_start = time.monotonic()
    first_pass = fallback_extract_from_search(
        query=query,
        category=category,
        budget_max=budget_max,
        max_results=target_count,
        search_terms=cleaned_terms[:3],
        deadline_ts=hard_deadline,
        max_terms=3,
        max_cards_per_term=4,
        max_snapshot_fetches=0,
        search_timeout=4,
        snapshot_timeout=3,
        phase="first_pass",
    )
    _timing_log(
        "fallback_phase_duration",
        phase="first_pass",
        duration_ms=round((time.monotonic() - first_phase_start) * 1000, 1),
        returned_count=len(first_pass.get("products", [])),
    )
    _add_products(first_pass.get("products"))
    workflow_errors.extend(str(item) for item in first_pass.get("errors", []) if str(item).strip())
    search_pages_loaded += int(first_pass.get("search_pages_loaded", 0) or 0)
    if len(collected) >= quick_target_count:
        return _finish({"products": collected[:target_count]}, "enough_products_after_first_pass")

    # 2) Secondary deterministic pass with broad term before using Nova Act.
    if len(collected) < quick_target_count and time.monotonic() < hard_deadline:
        second_phase_start = time.monotonic()
        broad_terms = _dedupe_terms([query, *cleaned_terms])
        second_pass = fallback_extract_from_search(
            query=query,
            category=category,
            budget_max=budget_max,
            max_results=quick_target_count - len(collected),
            search_terms=broad_terms,
            deadline_ts=hard_deadline,
            max_terms=1,
            max_cards_per_term=4,
            max_snapshot_fetches=0,
            search_timeout=4,
            snapshot_timeout=3,
            phase="second_pass",
        )
        _timing_log(
            "fallback_phase_duration",
            phase="second_pass",
            duration_ms=round((time.monotonic() - second_phase_start) * 1000, 1),
            returned_count=len(second_pass.get("products", [])),
        )
        _add_products(second_pass.get("products"))
        workflow_errors.extend(str(item) for item in second_pass.get("errors", []) if str(item).strip())
        search_pages_loaded += int(second_pass.get("search_pages_loaded", 0) or 0)
    if len(collected) >= quick_target_count:
        return _finish({"products": collected[:target_count]}, "enough_products_after_second_pass")

    # 3) Only if deterministic extraction is insufficient, try one short Nova Act attempt.
    if len(collected) < quick_target_count and NOVA_ACT_KEY and time.monotonic() < (hard_deadline - 8):
        act_term = (cleaned_terms[:1] or [query])[0]
        act_start = time.monotonic()
        _timing_log(
            "nova_act_start",
            term=act_term,
            max_steps=3,
            timeout_s=12,
        )
        try:
            with NovaAct(
                starting_page=build_starting_page(query, [act_term]),
                nova_act_api_key=NOVA_ACT_KEY,
                ignore_https_errors=True,
            ) as nova:
                result = nova.act_get(
                    build_prompt(act_term, category, budget_max),
                    schema=build_schema(1),
                    max_steps=3,
                    timeout=12,
                )
                _timing_log(
                    "nova_act_end",
                    ok=True,
                    duration_ms=round((time.monotonic() - act_start) * 1000, 1),
                )
                payload = result.parsed_response
                products = payload.get("products") if isinstance(payload, dict) else None
                _add_products(products)
        except Exception as exc:  # noqa: BLE001
            _timing_log(
                "nova_act_end",
                ok=False,
                duration_ms=round((time.monotonic() - act_start) * 1000, 1),
                error=str(exc),
            )
            live_failure_error = f"Nova Act live workflow failed for jumia: {exc}"
            workflow_errors.append(live_failure_error)
    if len(collected) >= quick_target_count:
        return _finish({"products": collected[:target_count]}, "enough_products_after_nova_act")

    if len(collected) == 0:
        if live_failure_error:
            return _finish(
                {
                    "products": [],
                    "error": live_failure_error,
                    "error_type": "live_actuator_failure",
                },
                "live_actuator_failure",
            )
        if search_pages_loaded == 0 and workflow_errors:
            return _finish(
                {
                    "products": [],
                    "error": workflow_errors[-1],
                    "error_type": "search_fetch_failure",
                },
                "search_fetch_failure",
            )

    return _finish({"products": collected[:target_count]}, "completed_with_products")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NovaPilot Jumia workflow")
    parser.add_argument(
        "--query",
        default="Find laptops under NGN 800000 for UI/UX design",
        help="Shopping query to execute on Jumia",
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

    result = run_jumia_workflow(
        args.query,
        args.category,
        args.budget_max,
        args.max_results,
        [str(term).strip() for term in search_terms if str(term).strip()][: args.max_search_terms],
    )
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

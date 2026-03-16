"""Amazon product extraction with deterministic search parsing plus Nova Act fallback.

Usage (PowerShell):
  $env:NOVA_API_KEY="your_nova_key"
  python scripts/amazon_workflow.py --query "Find laptops under NGN 800000 for UI/UX design"
"""

from __future__ import annotations

import argparse
import gzip
import html
from http.cookiejar import CookieJar
import json
import os
import re
import sys
import time
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen
from typing import Any

from nova_act import NovaAct

NOVA_ACT_KEY = os.getenv("NOVA_ACT_API_KEY") or os.getenv("NOVA_API_KEY")
AMAZON_NOVA_ACT_TIMEOUT_SECONDS = int(os.getenv("NOVAPILOT_AMAZON_NOVA_ACT_TIMEOUT_SECONDS", "45"))
AMAZON_NOVA_ACT_MAX_STEPS = int(os.getenv("NOVAPILOT_AMAZON_NOVA_ACT_MAX_STEPS", "10"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


AMAZON_BASE = "https://www.amazon.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

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
    "phone",
    "smartphone",
    "laptop",
    "tablet",
    "headphone",
    "earbuds",
    "earphones",
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
    "renewed",
    "refurbished",
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


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", html.unescape(value)).strip()
    return normalized or None


def _strip_html_tags(fragment: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", fragment)
    return _clean_text(no_tags) or ""


def _normalize_amazon_product_url(value: str | None) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.startswith("/"):
        text = urljoin(AMAZON_BASE, text)
    if not text.startswith("http://") and not text.startswith("https://"):
        return None

    parsed = urlparse(text)
    host = (parsed.netloc or "").lower()
    if "amazon." not in host:
        return None

    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", text, flags=re.IGNORECASE)
    if asin_match:
        return f"{AMAZON_BASE}/dp/{asin_match.group(1).upper()}"
    return None


def _normalize_image_url(value: str | None) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.startswith("//"):
        text = f"https:{text}"
    if text.startswith("/"):
        text = urljoin(AMAZON_BASE, text)
    if not text.startswith("http://") and not text.startswith("https://"):
        return None
    lowered = text.lower()
    if lowered.startswith("data:"):
        return None
    allowed_hosts = (
        "amazon.com",
        "media-amazon.com",
        "images-amazon.com",
        "ssl-images-amazon.com",
        "m.media-amazon.com",
        "images-na.ssl-images-amazon.com",
    )
    if not any(host in lowered for host in allowed_hosts):
        return None
    return text


def _is_valid_amazon_product_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower().strip()
    if not lowered.startswith("https://") and not lowered.startswith("http://"):
        return False
    if "amazon." not in lowered:
        return False
    if "/s?" in lowered and "k=" in lowered:
        return False
    return bool(re.search(r"/(?:dp|gp/product)/[a-z0-9]{10}(?:[/?]|$)", lowered, flags=re.IGNORECASE))


def _parse_price_value(value: str | None) -> float | None:
    if not value:
        return None
    matches = re.findall(r"\d[\d,]*(?:\.\d+)?", value)
    if not matches:
        return None
    try:
        return float(matches[0].replace(",", ""))
    except ValueError:
        return None


def _price_to_currency(value: str | None) -> str | None:
    if not value:
        return None
    upper = value.upper()
    if "$" in value or "USD" in upper:
        return "USD"
    if "EUR" in upper or "€" in value:
        return "EUR"
    if "GBP" in upper or "£" in value:
        return "GBP"
    return "USD"


def _candidate_group_key(item: dict[str, Any]) -> str:
    title = str(item.get("name") or "").lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", title)
    tokens = [token for token in cleaned.split() if token and token not in DEDUPLICATION_STOPWORDS]
    if tokens:
        return " ".join(tokens[:10])
    return str(item.get("product_url") or "").strip().lower()


def _candidate_score(
    item: dict[str, Any],
    *,
    query: str,
    term: str,
    category: str,
    budget_max: float | None,
) -> float:
    name = str(item.get("name") or "")
    details = str(item.get("details") or "")
    text = f"{name} {details}".lower()
    price = _parse_price_value(str(item.get("amount") or ""))
    score = 0.0

    query_tokens = _significant_tokens(term, query)
    match_count = sum(1 for token in query_tokens if token in text)
    score += min(match_count, 6) * 1.5

    if category.lower() == "laptop":
        if "16gb" in text:
            score += 1.5
        if "512gb" in text or "512 gb" in text:
            score += 1.25
        if any(token in text for token in ["core i7", "core i5", "ryzen 7", "ryzen 5"]):
            score += 1.0
    elif category.lower() == "tablet":
        if any(token in text for token in ["8gb", "128gb", "256gb", "stylus"]):
            score += 1.2
    elif category.lower() == "smartphone":
        if any(token in text for token in ["8gb", "128gb", "256gb", "5g"]):
            score += 1.2

    rating = item.get("rating")
    if isinstance(rating, (int, float)):
        score += min(float(rating), 5.0) * 0.35

    if item.get("image_url"):
        score += 0.2

    if price is not None and budget_max is not None and budget_max > 0:
        if price <= budget_max:
            closeness = 1.0 - abs(budget_max - price) / budget_max
            score += max(0.0, closeness) * 1.5
        else:
            score -= min(3.0, ((price - budget_max) / budget_max) * 8.0)

    return round(score, 3)


def _select_best_candidates(
    candidates: list[dict[str, Any]],
    *,
    target_count: int,
) -> list[dict[str, Any]]:
    ranked = sorted(
        candidates,
        key=lambda item: (
            float(item.get("_candidate_score", 0.0)),
            float(item.get("rating") or 0.0),
            1 if item.get("image_url") else 0,
        ),
        reverse=True,
    )

    selected: list[dict[str, Any]] = []
    used_groups: set[str] = set()

    for candidate in ranked:
        group_key = _candidate_group_key(candidate)
        if group_key in used_groups:
            continue
        used_groups.add(group_key)
        selected.append({key: value for key, value in candidate.items() if not str(key).startswith("_")})
        if len(selected) >= target_count:
            return selected

    for candidate in ranked:
        cleaned = {key: value for key, value in candidate.items() if not str(key).startswith("_")}
        candidate_url = str(cleaned.get("product_url") or "").strip().lower()
        if any(str(item.get("product_url") or "").strip().lower() == candidate_url for item in selected):
            continue
        selected.append(cleaned)
        if len(selected) >= target_count:
            break
    return selected


def _is_relevant_for_category(name: str | None, category: str) -> bool:
    text = (name or "").lower()
    if not text:
        return False

    blocked = {
        "laptop": ("bag", "sleeve", "skin", "sticker", "backpack", "course", "book", "dock", "adapter"),
        "smartphone": (
            "case",
            "cover",
            "charger",
            "screen protector",
            "earphone",
            "tempered glass",
            "power bank",
            "replacement",
        ),
        "tablet": (
            "case",
            "cover",
            "screen protector",
            "keyboard case",
            "stylus only",
            "graphic tablet",
            "graphics tablet",
            "drawing tablet",
            "drawing pad",
            "pen tablet",
            "digitizer",
            "wacom",
            "huion",
            "ugee",
            "xp-pen",
            "veikk",
        ),
        "audio": ("case", "cover", "speaker", "microphone", "cable", "adapter"),
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
            "thinkpad",
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
    if any(term in text for term in allowed):
        return True

    if category.lower() == "laptop":
        return any(token in text for token in ["intel", "ryzen", "ssd", "ram"])
    if category.lower() == "smartphone":
        return any(token in text for token in ["5g", "128gb", "256gb", "android", "ios"])
    if category.lower() == "tablet":
        return any(token in text for token in ["10.1", "11", "12.9", "stylus"])
    return False


def _decode_response(raw: bytes, content_type: str, content_encoding: str) -> str:
    encoding = (content_encoding or "").lower().strip()
    if encoding == "gzip":
        try:
            raw = gzip.decompress(raw)
        except Exception:  # noqa: BLE001
            pass
    elif encoding == "deflate":
        try:
            raw = zlib.decompress(raw)
        except Exception:  # noqa: BLE001
            try:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:  # noqa: BLE001
                pass

    charset_match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    charset = charset_match.group(1) if charset_match else "utf-8"
    return raw.decode(charset, errors="replace")


def _build_request_headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, identity",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _build_http_opener():
    return build_opener(HTTPCookieProcessor(CookieJar()))


def _extract_page_title(html_text: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    return _strip_html_tags(match.group(1)) if match else None


def _extract_detail_page_image(html_text: str) -> str | None:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'"hiRes"\s*:\s*"([^"]+)"',
        r'"large"\s*:\s*"([^"]+)"',
        r'"mainUrl"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        candidate = html.unescape(match.group(1)).replace("\\/", "/")
        normalized = _normalize_image_url(candidate)
        if normalized:
            return normalized
    return None


def _enrich_product_from_detail_page(
    item: dict[str, Any],
    *,
    opener,
    timeout: int,
) -> dict[str, Any]:
    product_url = _normalize_amazon_product_url(item.get("product_url"))
    if not product_url:
        return item
    try:
        page = _http_get(product_url, timeout=timeout, opener=opener, referer=AMAZON_BASE)
    except Exception:  # noqa: BLE001
        return item

    detail_image = _extract_detail_page_image(page)
    if detail_image:
        item["image_url"] = detail_image
    detail_title = _extract_page_title(page)
    if detail_title and detail_title.lower() != "amazon.com":
        cleaned_title = re.sub(r"\s*:\s*amazon\.com.*$", "", detail_title, flags=re.IGNORECASE).strip()
        if cleaned_title and cleaned_title.lower() != "amazon.com":
            item["details"] = cleaned_title
    return item


def _http_probe(
    url: str,
    timeout: int = 15,
    opener=None,
    referer: str | None = None,
) -> dict[str, Any]:
    opener = opener or _build_http_opener()
    request = Request(url, headers=_build_request_headers(referer=referer))
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
            content_encoding = (response.headers.get("Content-Encoding", "") or "").lower().strip()
            body = _decode_response(raw, content_type, content_encoding)
            return {
                "url": url,
                "status_code": getattr(response, "status", 200),
                "ok": True,
                "page_title": _extract_page_title(body),
                "captcha_detected": "captcha" in body.lower(),
                "robot_check_detected": "sorry, we just need to make sure you're not a robot" in body.lower(),
                "search_result_cards": len(_extract_result_chunks(body)),
            }
    except HTTPError as exc:
        body = exc.read()
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        content_encoding = (exc.headers.get("Content-Encoding", "") if exc.headers else "") or ""
        decoded_body = _decode_response(body, content_type, content_encoding) if body else ""
        return {
            "url": url,
            "status_code": exc.code,
            "ok": False,
            "error": str(exc),
            "page_title": _extract_page_title(decoded_body),
            "captcha_detected": "captcha" in decoded_body.lower(),
            "robot_check_detected": "sorry, we just need to make sure you're not a robot" in decoded_body.lower(),
            "search_result_cards": len(_extract_result_chunks(decoded_body)),
        }
    except URLError as exc:
        return {
            "url": url,
            "status_code": None,
            "ok": False,
            "error": str(exc),
            "page_title": None,
            "captcha_detected": False,
            "robot_check_detected": False,
            "search_result_cards": 0,
        }


def _http_get(url: str, timeout: int = 15, opener=None, referer: str | None = None) -> str:
    opener = opener or _build_http_opener()

    last_exception: Exception | None = None
    for attempt in range(1, 4):
        request = Request(url, headers=_build_request_headers(referer=referer))
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
                content_encoding = (response.headers.get("Content-Encoding", "") or "").lower().strip()
            return _decode_response(raw, content_type, content_encoding)
        except HTTPError as exc:
            body = exc.read()
            content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
            content_encoding = (exc.headers.get("Content-Encoding", "") if exc.headers else "") or ""
            decoded_body = _decode_response(body, content_type, content_encoding) if body else ""
            last_exception = exc
            if exc.code in {429, 503}:
                if attempt < 3:
                    time.sleep(attempt * 2)
                    continue
                if decoded_body:
                    return decoded_body
            raise
        except URLError as exc:
            last_exception = exc
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise
    if last_exception:
        raise last_exception
    raise RuntimeError(f"Amazon fetch failed for URL: {url}")


def collect_amazon_http_diagnostics(
    *,
    query: str,
    search_terms: list[str] | None = None,
    max_terms: int = 3,
    search_timeout: int = 10,
) -> dict[str, Any]:
    cleaned_terms = _dedupe_terms([term.strip() for term in (search_terms or [query]) if term.strip()])[:max_terms]
    opener = _build_http_opener()
    warmup = _http_probe(AMAZON_BASE, timeout=max(5, search_timeout), opener=opener)
    term_reports: list[dict[str, Any]] = []
    referer = AMAZON_BASE
    for term in cleaned_terms:
        search_url = f"{AMAZON_BASE}/s?k={quote_plus(term)}"
        probe = _http_probe(search_url, timeout=search_timeout, opener=opener, referer=referer)
        probe["term"] = term
        term_reports.append(probe)
        referer = search_url
    return {
        "query": query,
        "terms_tested": cleaned_terms,
        "warmup": warmup,
        "search_probes": term_reports,
        "amazon_base": AMAZON_BASE,
    }


def _extract_result_chunks(html_text: str) -> list[str]:
    chunks: list[str] = []
    starts = [
        match.start()
        for match in re.finditer(
            r'data-component-type=["\']s-search-result["\']',
            html_text,
            flags=re.IGNORECASE,
        )
    ]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else min(len(html_text), start + 16000)
        chunks.append(html_text[start:end])
    return chunks


def _parse_search_cards(html_text: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for chunk in _extract_result_chunks(html_text):
        asin_match = re.search(r'data-asin=["\']([A-Z0-9]{10})["\']', chunk, flags=re.IGNORECASE)
        if not asin_match:
            continue
        asin = asin_match.group(1).upper()

        href_match = re.search(
            r'<h2[^>]*>.*?<a[^>]+href=["\']([^"\']+)["\']',
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        url = _normalize_amazon_product_url(href_match.group(1) if href_match else f"/dp/{asin}")
        if not _is_valid_amazon_product_url(url):
            continue
        key = str(url).strip().lower()
        if key in seen_urls:
            continue

        title_match = re.search(
            r'<h2[^>]*>.*?<span[^>]*>(.*?)</span>',
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        title = _strip_html_tags(title_match.group(1)) if title_match else None
        if not title:
            title = f"Amazon product {asin}"

        price_match = re.search(
            r'<span[^>]*class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>(.*?)</span>',
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        price_text = _strip_html_tags(price_match.group(1)) if price_match else None
        amount = _parse_price_value(price_text)

        rating_match = re.search(
            r'<span[^>]*class=["\'][^"\']*a-icon-alt[^"\']*["\'][^>]*>(.*?)</span>',
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        rating_text = _strip_html_tags(rating_match.group(1)) if rating_match else None
        rating = _parse_price_value(rating_text)

        image_match = re.search(
            r'<img[^>]+class=["\'][^"\']*s-image[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        image_url = _normalize_image_url(image_match.group(1) if image_match else None)

        cards.append(
            {
                "name": title,
                "amount": amount,
                "currency_code": _price_to_currency(price_text),
                "rating": rating,
                "details": title,
                "product_url": url,
                "image_url": image_url,
            }
        )
        seen_urls.add(key)

    return cards


def fallback_extract_from_search(
    *,
    query: str,
    category: str,
    budget_max: float | None,
    max_results: int,
    search_terms: list[str],
    max_terms: int = 4,
    search_timeout: int = 10,
) -> dict[str, Any]:
    terms = _dedupe_terms(search_terms)[:max_terms] or [query]
    errors: list[str] = []
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    opener = _build_http_opener()

    try:
        _http_get(AMAZON_BASE, timeout=max(5, search_timeout), opener=opener)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"session_warmup: {exc}")

    for term in terms:
        search_url = f"{AMAZON_BASE}/s?k={quote_plus(term)}"
        try:
            page = _http_get(search_url, timeout=search_timeout, opener=opener, referer=AMAZON_BASE)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{term}: {exc}")
            continue

        if "captcha" in page.lower() or "sorry, we just need to make sure you're not a robot" in page.lower():
            errors.append(f"{term}: amazon_search_captcha")
            continue

        cards = _parse_search_cards(page)
        for card in cards:
            name = str(card.get("name") or "")
            product_url = str(card.get("product_url") or "")
            amount = card.get("amount")
            if not _is_valid_amazon_product_url(product_url):
                continue
            if product_url.lower() in seen_urls:
                continue
            if not _is_relevant_for_category(name, category):
                continue
            if budget_max is not None and (amount is None or float(amount) > budget_max):
                continue

            card["_candidate_score"] = _candidate_score(
                card,
                query=query,
                term=term,
                category=category,
                budget_max=budget_max,
            )
            candidates.append(card)
            seen_urls.add(product_url.lower())

        if len(candidates) >= max_results:
            break

    selected = _select_best_candidates(candidates, target_count=max_results)
    enriched: list[dict[str, Any]] = []
    for item in selected:
        enriched.append(
            _enrich_product_from_detail_page(
                item,
                opener=opener,
                timeout=max(6, min(search_timeout, 12)),
            )
        )
    return {"products": enriched, "errors": errors}


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
    return f"{AMAZON_BASE}/"


def build_prompt(
    query: str,
    country: str,
    category: str,
    search_terms: list[str],
    budget_max: float | None,
    budget_currency: str | None,
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
        "tablet": (
            "tablet cases, keyboard cases, stylus-only listings, screen protectors, chargers, "
            "accessories, phone results, graphics tablets, drawing tablets, pen tablets, pen displays, "
            "digitizers, Wacom/Huion/UGEE/XP-Pen listings, and any non-standalone-tablet result"
        ),
        "smartphone": "phone cases, chargers, screen protectors, earphones, replacement parts, accessories, and any non-phone result",
        "audio": "phone cases, speakers, microphones, cables, accessories, and any non-headphone result",
    }.get(category.lower(), "accessories and unrelated results")

    budget_guard = ""
    if budget_max is not None:
        currency_label = (budget_currency or "USD").upper()
        formatted_budget = f"{budget_max:.2f}" if currency_label == "USD" else f"{budget_max:.0f}"
        budget_guard = (
            f" Only keep products priced at or below the budget cap of {currency_label} {formatted_budget}. "
            "Do not include over-budget products."
        )

    return (
        "You are starting on Amazon.\n"
        f"Use these search terms in order: {ordered_terms}.\n"
        "If you are on the Amazon homepage, use the main search box to search the first term.\n"
        "If a location modal, sign-in prompt, or dismissible popover appears, close it and continue.\n"
        "If a simple robot/captcha page appears, try one refresh and continue if the search results become available.\n"
        "Stay on Amazon search results pages after you search.\n"
        "Stay on amazon.com only.\n"
        "Do not inspect sponsored rows, carousels, ads, or unrelated widgets.\n"
        f"Ignore and skip {excluded}.\n"
        f"Collect up to {max_results} real {product_type} listings from visible search result cards only.\n"
        "Inspect up to the first 8 visible strong matching cards.\n"
        "Compare those visible cards and return the best matches, not just the first ones you see.\n"
        "Open product detail pages only for the final shortlisted candidates when needed to capture a canonical product URL and primary image URL.\n"
        "If the current results are irrelevant, use the next search term in the Amazon search box.\n"
        "Use the raw user sentence first, then fall back to the more concrete follow-up terms if needed.\n"
        "Stop as soon as you have enough valid products."
        f"{budget_guard}\n"
        "Prefer extracting title, price, and rating directly from the visible search cards.\n"
        "Return only product detail page URLs, never search or category URLs.\n"
        "Ensure 'product_url' is an absolute https URL on www.amazon.com and points to a real product page.\n"
        "Do not return amazon.ng, search URLs, redirect URLs, or category URLs.\n"
        "For image_url, use the main product image from the product detail page when available; otherwise use the search-card image.\n"
        "Use 'rating' and 'details' from the search results when visible; otherwise return null.\n"
        "Return only the structured response requested by the schema."
    )


def run_amazon_workflow(
    query: str,
    country: str = "Nigeria",
    category: str = "electronics",
    budget_max: float | None = None,
    budget_currency: str | None = "USD",
    max_results: int = 5,
    search_terms: list[str] | None = None,
) -> Any:
    cleaned_terms = _dedupe_terms([query.strip(), *[term.strip() for term in (search_terms or [query]) if term.strip()]])
    target_count = max(1, min(max_results, 5))
    quick_target_count = min(target_count, 3)
    collected: list[dict[str, Any]] = []
    workflow_errors: list[str] = []
    seen_urls: set[str] = set()
    debug: dict[str, Any] = {
        "query": query,
        "country": country,
        "category": category,
        "budget_max": budget_max,
        "budget_currency": budget_currency,
        "target_count": target_count,
        "search_terms": cleaned_terms,
        "first_pass_product_count": 0,
        "first_pass_errors": [],
        "second_pass_product_count": 0,
        "second_pass_errors": [],
        "nova_act_attempted": False,
        "nova_act_error": None,
        "final_collected_count": 0,
    }

    def _add_products(items: Any) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            product_url = _normalize_amazon_product_url(item.get("product_url"))
            name = _clean_text(str(item.get("name") or "")) or None
            amount = item.get("amount")
            if amount is None and item.get("price_text"):
                amount = _parse_price_value(str(item.get("price_text")))
            currency_code = str(item.get("currency_code") or "").strip() or "USD"
            image_url = _normalize_image_url(item.get("image_url"))
            if not _is_valid_amazon_product_url(product_url):
                continue
            if not _is_relevant_for_category(name, category):
                continue
            if budget_max is not None and (amount is None or float(amount) > budget_max):
                continue
            key = product_url.strip().lower()
            if not key or key in seen_urls:
                continue
            seen_urls.add(key)
            collected.append(
                {
                    "name": name,
                    "amount": amount,
                    "currency_code": currency_code,
                    "rating": item.get("rating"),
                    "details": _clean_text(str(item.get("details") or name or "")),
                    "product_url": product_url,
                    "image_url": image_url,
                }
            )
            if len(collected) >= target_count:
                return

    first_pass = fallback_extract_from_search(
        query=query,
        category=category,
        budget_max=budget_max,
        max_results=target_count,
        search_terms=cleaned_terms[:4],
        max_terms=4,
        search_timeout=10,
    )
    debug["first_pass_product_count"] = len(first_pass.get("products") or [])
    debug["first_pass_errors"] = [str(item) for item in first_pass.get("errors", []) if str(item).strip()]
    _add_products(first_pass.get("products"))
    workflow_errors.extend(str(item) for item in first_pass.get("errors", []) if str(item).strip())
    if len(collected) >= quick_target_count:
        debug["final_collected_count"] = len(collected[:target_count])
        return {"products": collected[:target_count], "debug": debug}

    follow_up_terms = cleaned_terms[4:] if len(cleaned_terms) > 4 else cleaned_terms[1:]
    broad_terms = _dedupe_terms([*follow_up_terms, query])
    if broad_terms and len(collected) < quick_target_count:
        second_pass = fallback_extract_from_search(
            query=query,
            category=category,
            budget_max=budget_max,
            max_results=target_count - len(collected),
            search_terms=broad_terms,
            max_terms=3,
            search_timeout=10,
        )
        debug["second_pass_product_count"] = len(second_pass.get("products") or [])
        debug["second_pass_errors"] = [str(item) for item in second_pass.get("errors", []) if str(item).strip()]
        _add_products(second_pass.get("products"))
        workflow_errors.extend(str(item) for item in second_pass.get("errors", []) if str(item).strip())
    if len(collected) >= quick_target_count:
        debug["final_collected_count"] = len(collected[:target_count])
        return {"products": collected[:target_count], "debug": debug}

    live_failure_error: str | None = None
    if NOVA_ACT_KEY:
        debug["nova_act_attempted"] = True
        act_term = (cleaned_terms[:1] or [query])[0]
        try:
            with NovaAct(
                starting_page=build_starting_page(query, [act_term]),
                nova_act_api_key=NOVA_ACT_KEY,
                ignore_https_errors=True,
            ) as nova:
                payload = nova.act_get(
                    build_prompt(
                        query,
                        country,
                        category,
                        cleaned_terms or [query],
                        budget_max,
                        budget_currency,
                        min(2, max(1, target_count - len(collected))),
                    ),
                    schema=build_schema(min(2, max(1, target_count - len(collected)))),
                    max_steps=max(6, AMAZON_NOVA_ACT_MAX_STEPS),
                    timeout=max(20, AMAZON_NOVA_ACT_TIMEOUT_SECONDS),
                ).parsed_response
                products = payload.get("products") if isinstance(payload, dict) else None
                _add_products(products)
        except Exception as exc:  # noqa: BLE001
            live_failure_error = f"Nova Act live workflow failed for amazon: {exc}"
            workflow_errors.append(live_failure_error)
            debug["nova_act_error"] = str(exc)

    if collected:
        debug["final_collected_count"] = len(collected[:target_count])
        return {"products": collected[:target_count], "debug": debug}

    if live_failure_error:
        debug["final_collected_count"] = 0
        return {
            "products": [],
            "error": live_failure_error,
            "error_type": "live_actuator_failure",
            "debug": debug,
        }
    if workflow_errors:
        debug["final_collected_count"] = 0
        return {"products": [], "errors": workflow_errors, "debug": debug}
    debug["final_collected_count"] = 0
    return {"products": [], "debug": debug}


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
        "--budget-currency",
        default="USD",
        help="Currency code for the budget max passed to the Amazon workflow",
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
        args.budget_currency,
        args.max_results,
        [str(term).strip() for term in search_terms if str(term).strip()][: args.max_search_terms],
    )
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

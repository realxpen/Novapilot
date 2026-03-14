"""Probe Nova + Jumia HTTPS reachability in the same env path used by NovaActClient.

Usage:
  python scripts/nova_subprocess_connectivity_probe.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.clients.nova_act_client import build_nova_act_child_env  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.utils.secrets import mask_secret  # noqa: E402


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _extract_exception_chain(exc: Exception) -> list[dict[str, str]]:
    chain: list[dict[str, str]] = []
    current: Exception | None = exc
    for _ in range(8):
        if current is None:
            break
        chain.append(
            {
                "type": f"{current.__class__.__module__}.{current.__class__.__name__}",
                "message": str(current),
            }
        )
        next_exc = current.__cause__ or current.__context__
        current = next_exc if isinstance(next_exc, Exception) else None
    return chain


def _probe_url(url: str, timeout_seconds: float) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            return {
                "url": url,
                "timeout_seconds": timeout_seconds,
                "started_at": started_at,
                "ok": True,
                "connectivity_ok": True,
                "duration_ms": elapsed_ms,
                "status_code": getattr(response, "status", None),
                "content_type": response.headers.get("Content-Type"),
                "http_error": False,
                "exception_type": None,
                "exception_message": None,
                "exception_chain": [],
                "winerror_10013": False,
            }
    except HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        # HTTPError means endpoint is reachable; request succeeded at transport layer.
        return {
            "url": url,
            "timeout_seconds": timeout_seconds,
            "started_at": started_at,
            "ok": True,
            "connectivity_ok": True,
            "duration_ms": elapsed_ms,
            "status_code": exc.code,
            "content_type": exc.headers.get("Content-Type") if exc.headers else None,
            "http_error": True,
            "exception_type": f"{exc.__class__.__module__}.{exc.__class__.__name__}",
            "exception_message": str(exc),
            "exception_chain": _extract_exception_chain(exc),
            "winerror_10013": False,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        chain = _extract_exception_chain(exc)
        return {
            "url": url,
            "timeout_seconds": timeout_seconds,
            "started_at": started_at,
            "ok": False,
            "connectivity_ok": False,
            "duration_ms": elapsed_ms,
            "status_code": None,
            "content_type": None,
            "http_error": False,
            "exception_type": f"{exc.__class__.__module__}.{exc.__class__.__name__}",
            "exception_message": str(exc),
            "exception_chain": chain,
            "winerror_10013": any("WinError 10013" in item.get("message", "") for item in chain)
            or "WinError 10013" in str(exc),
        }


def _classify(nova_ok: bool, jumia_ok: bool) -> str:
    if not nova_ok and not jumia_ok:
        return "both"
    if not nova_ok and jumia_ok:
        return "nova_only"
    if nova_ok and not jumia_ok:
        return "jumia_only"
    return "none"


def _run_child(timeout_seconds: float, jumia_url: str) -> dict[str, Any]:
    nova_url = "https://api.nova.amazon.com/"
    probes = [
        _probe_url(nova_url, timeout_seconds),
        _probe_url(jumia_url, timeout_seconds),
    ]
    nova_probe = probes[0]
    jumia_probe = probes[1]
    return {
        "mode": "child",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "child_env": {
            "has_nova_act_api_key": bool(os.environ.get("NOVA_ACT_API_KEY")),
            "masked_nova_act_api_key": mask_secret(os.environ.get("NOVA_ACT_API_KEY")),
            "has_nova_api_key": bool(os.environ.get("NOVA_API_KEY")),
            "masked_nova_api_key": mask_secret(os.environ.get("NOVA_API_KEY")),
        },
        "targets": probes,
        "failure_scope": _classify(
            bool(nova_probe.get("connectivity_ok", False)),
            bool(jumia_probe.get("connectivity_ok", False)),
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Nova/Jumia HTTPS in Nova workflow subprocess env")
    parser.add_argument("--child", action="store_true", help="Internal mode: run probes in child process.")
    parser.add_argument("--timeout-seconds", type=float, default=6.0, help="Per-request timeout seconds.")
    parser.add_argument(
        "--jumia-url",
        default="https://www.jumia.com.ng/catalog/?q=Samsung+Galaxy+A55+8GB+256GB+phone",
        help="Jumia URL to probe.",
    )
    args = parser.parse_args()

    if args.child:
        report = _run_child(args.timeout_seconds, args.jumia_url)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    settings = get_settings()
    child_env = build_nova_act_child_env(settings.nova_api_key)
    child_cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child",
        "--timeout-seconds",
        str(args.timeout_seconds),
        "--jumia-url",
        args.jumia_url,
    ]
    completed = subprocess.run(
        child_cmd,
        cwd=str(REPO_ROOT),
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )
    payload: dict[str, Any] | str
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        payload = completed.stdout

    report = {
        "mode": "parent",
        "env_builder": "app.clients.nova_act_client.build_nova_act_child_env",
        "settings_nova_api_key_present": bool(settings.nova_api_key),
        "masked_settings_nova_api_key": mask_secret(settings.nova_api_key),
        "child_env_has_nova_act_api_key": bool(child_env.get("NOVA_ACT_API_KEY")),
        "child_env_has_nova_api_key": bool(child_env.get("NOVA_API_KEY")),
        "child_command": child_cmd,
        "child_returncode": completed.returncode,
        "child_stdout": payload,
        "child_stderr": completed.stderr,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

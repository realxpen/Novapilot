"""Minimal connectivity diagnostics for Nova Act actuator failures.

Checks:
1. DNS resolution for api.nova.amazon.com
2. Outbound HTTPS/TLS connectivity to api.nova.amazon.com:443
3. Whether this process can open sockets normally
4. Whether proxy environment variables are set
5. Whether Nova Act API key environment variables are present
"""

from __future__ import annotations

import os
import socket
import ssl
import sys
from dataclasses import dataclass
from typing import Any


TARGET_HOST = "api.nova.amazon.com"
TARGET_PORT = 443
SOCKET_TIMEOUT_SECONDS = 10


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: dict[str, Any]


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def run_socket_open_check() -> CheckResult:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT_SECONDS)
        sock.close()
        return CheckResult(
            name="local_socket_open",
            ok=True,
            details={"message": "Process can create and close a TCP socket."},
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="local_socket_open",
            ok=False,
            details={"error": repr(exc)},
        )


def run_dns_check(host: str, port: int) -> CheckResult:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses: list[str] = []
        for info in infos:
            sockaddr = info[4]
            if sockaddr:
                addresses.append(str(sockaddr[0]))
        deduped = sorted(set(addresses))
        return CheckResult(
            name="dns_resolution",
            ok=bool(deduped),
            details={
                "host": host,
                "port": port,
                "resolved_addresses": deduped,
                "address_count": len(deduped),
            },
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="dns_resolution",
            ok=False,
            details={"host": host, "port": port, "error": repr(exc)},
        )


def run_https_check(host: str, port: int) -> CheckResult:
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT_SECONDS) as raw_sock:
            with context.wrap_socket(raw_sock, server_hostname=host) as tls_sock:
                certificate = tls_sock.getpeercert()
                cipher = tls_sock.cipher()
                tls_version = tls_sock.version()
        return CheckResult(
            name="outbound_https_tls",
            ok=True,
            details={
                "host": host,
                "port": port,
                "tls_version": tls_version,
                "cipher": cipher[0] if cipher else None,
                "peer_subject": certificate.get("subject") if isinstance(certificate, dict) else None,
            },
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="outbound_https_tls",
            ok=False,
            details={"host": host, "port": port, "error": repr(exc)},
        )


def collect_proxy_env() -> CheckResult:
    keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ]
    found = {key: os.environ.get(key) for key in keys if os.environ.get(key)}
    return CheckResult(
        name="proxy_environment",
        ok=True,
        details={
            "found_proxy_env": found,
            "proxy_env_present": bool(found),
        },
    )


def collect_api_key_env() -> CheckResult:
    key_names = ["NOVA_ACT_API_KEY", "NOVA_API_KEY"]
    found = {
        key: {
            "present": bool(os.environ.get(key)),
            "masked_value": mask_secret(os.environ.get(key)),
            "length": len(os.environ.get(key, "")),
        }
        for key in key_names
    }
    any_present = any(item["present"] for item in found.values())
    return CheckResult(
        name="nova_api_key_environment",
        ok=any_present,
        details={
            "api_key_present": any_present,
            "env": found,
        },
    )


def print_report(results: list[CheckResult]) -> None:
    overall_ok = all(result.ok for result in results if result.name != "proxy_environment")

    print("Nova Act Connectivity Diagnostic")
    print("=" * 33)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {sys.platform}")
    print(f"Target: {TARGET_HOST}:{TARGET_PORT}")
    print(f"Overall status: {'PASS' if overall_ok else 'FAIL'}")
    print()

    for result in results:
        print(f"[{'PASS' if result.ok else 'FAIL'}] {result.name}")
        for key, value in result.details.items():
            print(f"  - {key}: {value}")
        print()

    print("Interpretation")
    print("-" * 14)
    dns_ok = next(result.ok for result in results if result.name == "dns_resolution")
    https_ok = next(result.ok for result in results if result.name == "outbound_https_tls")
    socket_ok = next(result.ok for result in results if result.name == "local_socket_open")
    key_ok = next(result.ok for result in results if result.name == "nova_api_key_environment")
    proxy_info = next(result for result in results if result.name == "proxy_environment")

    if not socket_ok:
        print("This process cannot open sockets normally. The issue is local OS/runtime permissions.")
    elif not dns_ok:
        print("DNS lookup failed. The machine cannot resolve api.nova.amazon.com.")
    elif not https_ok:
        print("DNS works, but outbound HTTPS/TLS to api.nova.amazon.com:443 failed.")
        if proxy_info.details.get("proxy_env_present"):
            print("Proxy environment variables are set, so proxy routing may be interfering.")
        else:
            print("No proxy environment variables were found in this process.")
    elif not key_ok:
        print("Network looks fine, but the Nova Act API key environment variable is missing.")
    else:
        print("Local environment checks passed. If Nova Act still fails, the problem is likely upstream in workflow logic or remote service behavior.")


def main() -> int:
    results = [
        run_socket_open_check(),
        run_dns_check(TARGET_HOST, TARGET_PORT),
        run_https_check(TARGET_HOST, TARGET_PORT),
        collect_proxy_env(),
        collect_api_key_env(),
    ]
    print_report(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

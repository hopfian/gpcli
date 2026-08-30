"""DNS fail-open patch.

The local resolver intermittently fails to resolve *.grameenphone.com.
This module installs a getaddrinfo patch that, on resolution failure,
resolves the host over DNS-over-HTTPS (using direct resolver IPs so the
fallback itself never needs DNS), caches the answer, and retries.

Adapted from the gpcloud-cli toolchain where the same ISP-level flakiness
was first encountered.
"""

from __future__ import annotations

import socket
import threading

import httpx

_local = threading.local()
_patched_hosts: dict[str, str] = {}
_orig_getaddrinfo = socket.getaddrinfo
_installed = False

_DOH_RESOLVERS = (
    # (ip, host header, path) — certs cover the raw IPs, so no DNS needed
    ("8.8.8.8", "dns.google", "/resolve"),
    ("1.1.1.1", "cloudflare-dns.com", "/dns-query"),
)


def _doh_resolve(host: str) -> str | None:
    for ip, host_header, path in _DOH_RESOLVERS:
        try:
            r = httpx.get(
                f"https://{ip}{path}",
                params={"name": host, "type": "A"},
                headers={"Host": host_header},
                timeout=10,
            )
            for answer in r.json().get("Answer", []):
                if answer.get("type") == 1:  # A record
                    return str(answer["data"])
        except Exception:
            continue
    return None


def _patched_getaddrinfo(host, port, *args, **kwargs):
    try:
        return _orig_getaddrinfo(host, port, *args, **kwargs)
    except socket.gaierror:
        if host in _patched_hosts:
            return _orig_getaddrinfo(_patched_hosts[host], port, *args, **kwargs)
        if getattr(_local, "resolving", False):
            raise  # recursion guard (the DoH lookup itself resolves names)
        _local.resolving = True
        try:
            ip = _doh_resolve(host)
            if ip:
                _patched_hosts[host] = ip
                return _orig_getaddrinfo(ip, port, *args, **kwargs)
        finally:
            _local.resolving = False
        raise


def install_dns_fallback() -> None:
    """Install the fail-open getaddrinfo patch (idempotent)."""
    global _installed
    if _installed:
        return
    socket.getaddrinfo = _patched_getaddrinfo
    _installed = True


def resolved_via_fallback(host: str) -> bool:
    """True if `host` is currently pinned via the DoH fallback cache."""
    return host in _patched_hosts

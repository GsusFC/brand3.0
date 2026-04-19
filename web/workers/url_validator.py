"""URL validation + normalization for user-submitted analysis requests.

Rejects schemes other than http/https, private IPs, localhost, hostnames
without a dot, and URLs over 2048 chars. Normalizes to lowercase host +
trimmed trailing slash. Optional domain blocklist via env var.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse, urlunparse

MAX_URL_LENGTH = 2048
RESOLVE_TIMEOUT_S = 3.0

_LOCAL_HOSTS = {"localhost", "localhost.localdomain", "0.0.0.0", "::", "ip6-localhost"}


def _blocked_domains() -> set[str]:
    raw = os.environ.get("BRAND3_BLOCKED_DOMAINS", "")
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


def _is_private_or_loopback(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_safely(host: str) -> tuple[bool, str]:
    """Return (ok, reason). Fail on resolution error or private IPs."""
    socket.setdefaulttimeout(RESOLVE_TIMEOUT_S)
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False, "hostname does not resolve"
    except OSError as exc:
        return False, f"dns error: {exc}"
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        if _is_private_or_loopback(ip_str):
            return False, f"resolves to private/loopback address ({ip_str})"
    return True, ""


def validate_url(url: str) -> tuple[bool, str]:
    """Return ``(True, normalized_url)`` or ``(False, error_message)``."""
    if not isinstance(url, str) or not url.strip():
        return False, "url is empty"
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        return False, f"url exceeds {MAX_URL_LENGTH} chars"

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "only http:// and https:// are allowed"

    host = (parsed.hostname or "").lower()
    if not host:
        return False, "url is missing a hostname"
    if host in _LOCAL_HOSTS:
        return False, "localhost and loopback hosts are not allowed"
    if "." not in host:
        return False, "hostname must contain a dot (e.g. example.com)"

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and _is_private_or_loopback(str(ip)):
        return False, "private/loopback IPs are not allowed"

    blocked = _blocked_domains()
    if blocked:
        if any(host == d or host.endswith("." + d) for d in blocked):
            return False, "domain is on the blocklist"

    if ip is None:
        ok, reason = _resolve_safely(host)
        if not ok:
            return False, reason

    path = parsed.path or ""
    if path == "/":
        path = ""
    normalized = urlunparse(
        (parsed.scheme, host + (f":{parsed.port}" if parsed.port else ""),
         path, parsed.params, parsed.query, "")
    )
    return True, normalized

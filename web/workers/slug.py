"""Brand slug helpers — lightweight, no external deps."""

from __future__ import annotations

from urllib.parse import urlparse


def slug_from_url(url: str) -> str:
    """Return the registrable-domain stem (``a16z.com`` → ``a16z``)."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return "brand"
    parts = host.split(".")
    if len(parts) >= 2:
        return _clean(parts[-2])
    return _clean(parts[0])


def _clean(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in value)
    collapsed = "-".join(p for p in cleaned.split("-") if p)
    return collapsed or "brand"

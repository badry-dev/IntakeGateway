"""SSRF protection for caller-supplied URLs.

Validates scheme and resolved IP addresses before any server-side fetch so
preview endpoints, task imports, and OAuth token requests cannot be pointed at
cloud metadata services (169.254.169.254), loopback, or private network
ranges.

An escape hatch (`ALLOWED_SOURCE_HOSTS`, comma-separated) exists for legitimate
internal-source deployments; matching hosts bypass the private-range checks.

Residual risk: validation resolves DNS independently of the HTTP client, so a
rebinding resolver can still serve different answers to the guard and to the
connection. Re-validation per attempt narrows this window but does not close
it; fully closing it requires pinning the connection to the validated IP
(with correct Host/SNI) or a transport that re-checks the peer address.
"""

import ipaddress
import socket
from urllib.parse import urlparse

from loguru import logger

from app.core.config import settings


class SSRFBlockedError(ValueError):
    """Raised when a URL fails SSRF validation."""


def _allowed_hosts() -> set[str]:
    raw = getattr(settings, "ALLOWED_SOURCE_HOSTS", "") or ""
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def validate_url(url: str, *, resolve: bool = True) -> str:
    """Validate a caller-supplied URL for server-side fetching.

    Args:
        url: The URL to validate.
        resolve: When True (default), also resolve DNS and reject private,
            loopback, and link-local addresses — closing the DNS-rebinding gap
            for the actual connection, not just the hostname string.

    Returns:
        The validated URL (unchanged).

    Raises:
        SSRFBlockedError: If the URL is not http(s), has no host, resolves to a
            blocked address, or its hostname is not allowlisted.
    """
    if not url or not isinstance(url, str):
        raise SSRFBlockedError("URL is required")

    parsed = urlparse(url.strip())

    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFBlockedError(f"Only http/https URLs are allowed (got scheme {parsed.scheme!r})")

    host = parsed.hostname
    if not host:
        raise SSRFBlockedError("URL must include a host")

    # Literal IPs are checked directly; hostnames are resolved.
    try:
        candidate_addrs = [ipaddress.ip_address(host)]
    except ValueError:
        candidate_addrs = []

    allowed = _allowed_hosts()
    host_allowed = host.lower() in allowed

    if not candidate_addrs and resolve:
        # urlparse raises ValueError on attribute access for out-of-range
        # ports (http://example.com:99999/) — surface it as SSRFBlockedError,
        # not a 500.
        try:
            port = parsed.port
        except ValueError as e:
            raise SSRFBlockedError(f"URL has an invalid port: {e}") from e
        try:
            infos = socket.getaddrinfo(host, port or None)
            candidate_addrs = [ipaddress.ip_address(info[4][0]) for info in infos]
        except socket.gaierror as e:
            raise SSRFBlockedError(f"Cannot resolve host {host!r}: {e}") from e

    if not host_allowed:
        for addr in candidate_addrs:
            _reject_private(addr, host)

    return url.strip()


async def validate_url_async(url: str, *, resolve: bool = True) -> str:
    """Async variant of validate_url.

    socket.getaddrinfo is synchronous and has no timeout control; running it
    on the event loop would stall every other coroutine for the full resolver
    delay. Async call sites (fetch_json, OAuth token requests) must use this.
    """
    import asyncio

    return await asyncio.to_thread(validate_url, url, resolve=resolve)


def _reject_private(addr: ipaddress.IPv4Address | ipaddress.IPv6Address, host: str) -> None:
    if (
        addr.is_loopback
        or addr.is_link_local
        or addr.is_private
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    ):
        logger.warning(f"SSRF guard blocked request to {host!r} (resolved {addr})")
        raise SSRFBlockedError(
            f"Host {host!r} resolves to a non-public address ({addr}); "
            "blocked to prevent SSRF. Add it to ALLOWED_SOURCE_HOSTS if this "
            "source is intentional."
        )

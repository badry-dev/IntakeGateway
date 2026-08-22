"""Shared-token authentication for management endpoints.

When API_TOKEN is configured, every management route requires a matching
``X-API-Key`` header or ``Authorization: Bearer <token>``. This authenticates
the API but provides no per-user authorization (single shared secret).

Fail-closed: if API_TOKEN is unset while APP_ENV=production, startup refuses.
Development keeps open access with a startup warning.
"""

import hmac

from fastapi import HTTPException, Request
from loguru import logger

from app.core.config import settings

_CANDIDATE_HEADERS = ("x-api-key", "authorization")


def _extract_token(request: Request) -> str | None:
    for header in _CANDIDATE_HEADERS:
        value = request.headers.get(header)
        if not value:
            continue
        if header == "authorization":
            if value.lower().startswith("bearer "):
                return value[7:].strip()
            continue
        return value.strip()
    return None


def verify_api_token(token: str | None) -> bool:
    expected = settings.API_TOKEN
    if not expected:
        return True
    if not token:
        return False
    # Compare UTF-8 encoded bytes: hmac.compare_digest raises TypeError on
    # non-ASCII str input.
    return hmac.compare_digest(token.encode("utf-8"), expected.encode("utf-8"))


async def require_api_token(request: Request) -> None:
    """FastAPI dependency enforcing the shared API token when configured."""
    if not settings.API_TOKEN:
        return

    supplied = _extract_token(request)
    if not verify_api_token(supplied):
        # ASGI servers percent-decode paths, so control characters can reach
        # request.url.path — strip CR/LF to prevent log forging.
        safe_path = str(request.url.path).replace("\r", "").replace("\n", "")
        logger.warning(f"Rejected request to {safe_path}: missing or invalid API token")
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API token. Provide X-API-Key or Authorization: Bearer.",
        )


def enforce_api_token_configured() -> None:
    """Startup guard: refuse to boot an unauthenticated production API."""
    if settings.APP_ENV == "production" and not settings.API_TOKEN:
        raise RuntimeError(
            "Refusing to start: API_TOKEN must be set when APP_ENV=production "
            "(management endpoints would otherwise be unauthenticated)."
        )
    if not settings.API_TOKEN:
        logger.warning(
            "API_TOKEN is not set — management endpoints are UNAUTHENTICATED "
            "(allowed outside production)."
        )

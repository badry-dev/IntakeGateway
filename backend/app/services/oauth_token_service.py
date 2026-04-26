"""
OAuth2 token acquisition + refresh service (P0-A).

Supports the `client_credentials` and `refresh_token` grants from RFC 6749.
Tokens are persisted on the Task row encrypted at rest via Fernet
(matching the existing pattern for `Task.api_key` / `Task.password`).

PKCE / `state` are NOT applicable to `client_credentials` (no user-agent
redirect leg). They MUST be added if an `authorization_code` grant is later
introduced.

Concurrency model:
- In-process: an `asyncio.Lock` per task_id prevents thundering-herd refreshes
  when multiple coroutines in the same worker hit an expired token.
- Cross-process (Celery workers): not coordinated. Concurrent refreshes from
  multiple workers are tolerated; the last writer wins on the Task row, and
  any plaintext token returned to a caller stays valid until it expires.
  Most providers also accept multiple in-flight refresh requests for the same
  client. If a stricter guarantee becomes necessary, replace `_get_lock` with
  a DB advisory lock (e.g. `SELECT ... FOR UPDATE` on the task row).
"""
from __future__ import annotations

import asyncio
import datetime as _dt
from typing import Any, Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.core.encryption import decrypt_value, encrypt_value
from app.db.models.task import Task


# Locks are keyed by (task_id, id(running_loop)) because asyncio.Lock instances
# are loop-bound on first use. Celery entrypoints call asyncio.run(), which spins
# a fresh event loop per task invocation — caching a Lock keyed only by task_id
# would raise "<Lock> is bound to a different event loop" on the second call.
# We also opportunistically prune entries whose loop has been closed.
_TASK_LOCKS: dict[tuple[int, int], asyncio.Lock] = {}


async def _get_lock(task_id: int) -> asyncio.Lock:
    """Return (creating if needed) the per-task asyncio lock used to serialize refreshes."""
    loop = asyncio.get_running_loop()
    key = (task_id, id(loop))
    lock = _TASK_LOCKS.get(key)
    if lock is None:
        # Drop stale entries whose loops are no longer running. This keeps the
        # registry from growing unboundedly across many Celery invocations.
        stale = [
            k for k in list(_TASK_LOCKS.keys())
            if k[0] == task_id and k[1] != id(loop)
        ]
        for s in stale:
            _TASK_LOCKS.pop(s, None)
        lock = asyncio.Lock()
        _TASK_LOCKS[key] = lock
    return lock


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _is_expired(task: Task, skew_seconds: int) -> bool:
    """True if there is no cached token or it expires within `skew_seconds`."""
    if not task.oauth_access_token:
        return True
    if task.oauth_token_expires_at is None:
        # Unknown expiry — treat as expired so we proactively refresh.
        return True
    expires_at = task.oauth_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=_dt.timezone.utc)
    return (_utcnow() + _dt.timedelta(seconds=skew_seconds)) >= expires_at


def _legacy_static_token(task: Task) -> Optional[str]:
    """Read a static access_token from the legacy `oauth_config` JSON for back-compat."""
    cfg = task.oauth_config
    if isinstance(cfg, dict) and cfg.get("access_token"):
        try:
            return decrypt_value(cfg["access_token"])
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Failed to decrypt legacy oauth_config.access_token: {exc}")
            return None
    return None


def _build_token_request(task: Task, grant_type: str) -> dict[str, str]:
    """Build the form-encoded body for a token endpoint request (RFC 6749 §4.4 / §6)."""
    body: dict[str, str] = {"grant_type": grant_type}
    if task.oauth_client_id:
        body["client_id"] = task.oauth_client_id
    if task.oauth_client_secret:
        body["client_secret"] = decrypt_value(task.oauth_client_secret)
    if task.oauth_scope:
        body["scope"] = task.oauth_scope
    if task.oauth_audience:
        body["audience"] = task.oauth_audience
    if grant_type == "refresh_token":
        if not task.oauth_refresh_token:
            raise ValueError("refresh_token grant requires a stored refresh_token")
        body["refresh_token"] = decrypt_value(task.oauth_refresh_token)
    return body


def _persist_token_response(task: Task, db: Any, payload: dict[str, Any]) -> str:
    """
    Encrypt + persist the token response on the Task row.
    Returns the plaintext access_token for in-memory use by the caller.
    """
    access_token = payload.get("access_token")
    if not access_token:
        raise ValueError("Token endpoint response missing 'access_token'")

    expires_in = payload.get("expires_in")
    if isinstance(expires_in, (int, float)) and expires_in > 0:
        task.oauth_token_expires_at = _utcnow() + _dt.timedelta(seconds=int(expires_in))
    else:
        task.oauth_token_expires_at = None

    task.oauth_access_token = encrypt_value(str(access_token))

    # `refresh_token` rotation: most providers omit on client_credentials and may
    # rotate (or not) on refresh_token. Only overwrite when one is actually returned.
    new_refresh = payload.get("refresh_token")
    if new_refresh:
        task.oauth_refresh_token = encrypt_value(str(new_refresh))

    db.add(task)
    db.commit()
    return str(access_token)


async def _post_token_request(token_url: str, body: dict[str, str]) -> dict[str, Any]:
    """POST to the token endpoint. Logs status + body length only — never the body itself."""
    timeout = httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            token_url,
            data=body,
            headers={"Accept": "application/json"},
        )
    if resp.status_code >= 400:
        logger.error(
            f"OAuth token request failed: status={resp.status_code} "
            f"len={len(resp.content)} url={token_url}"
        )
        resp.raise_for_status()
    try:
        return resp.json()
    except Exception as exc:
        raise ValueError(f"Token endpoint returned non-JSON response: {exc}") from exc


async def get_access_token(
    task: Task,
    db: Any,
    force_refresh: bool = False,
) -> str:
    """
    Resolve a usable OAuth2 access token for the given Task.

    - Returns a static token for `oauth_grant_type in (None, 'static')` (back-compat
      with the legacy `oauth_config['access_token']` path).
    - Otherwise refreshes via the configured grant when expired or `force_refresh=True`.
    - Persists the new token (encrypted) on the Task row.
    - Coalesces concurrent refreshes per task_id via an asyncio.Lock.

    The returned plaintext token MUST NOT be logged.
    """
    grant_type = (task.oauth_grant_type or "static").lower()

    if grant_type == "static":
        # Prefer a server-managed cached static token if present
        if task.oauth_access_token:
            return decrypt_value(task.oauth_access_token)
        legacy = _legacy_static_token(task)
        if legacy:
            return legacy
        raise ValueError("OAuth task has no access_token configured")

    if grant_type not in ("client_credentials", "refresh_token"):
        raise ValueError(f"Unsupported oauth_grant_type: {task.oauth_grant_type!r}")

    if not task.oauth_token_url:
        raise ValueError(f"oauth_grant_type={grant_type} requires oauth_token_url")

    skew = settings.OAUTH_TOKEN_REFRESH_SKEW_SECONDS

    # Fast path: cached + valid + caller didn't force refresh.
    if not force_refresh and not _is_expired(task, skew):
        return decrypt_value(task.oauth_access_token)

    lock = await _get_lock(task.id)
    try:
        await asyncio.wait_for(lock.acquire(), timeout=settings.OAUTH_REFRESH_LOCK_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise TimeoutError(
            f"Timed out waiting for OAuth refresh lock on task {task.id}"
        ) from exc

    try:
        # Re-read from DB inside the lock so we pick up any refresh by a sibling coroutine.
        db.refresh(task)
        if not force_refresh and not _is_expired(task, skew):
            return decrypt_value(task.oauth_access_token)

        body = _build_token_request(task, grant_type)
        # Only log non-secret context. NEVER log `body` (contains client_secret/refresh_token).
        logger.info(
            f"OAuth token refresh: task_id={task.id} grant_type={grant_type} "
            f"token_url={task.oauth_token_url}"
        )
        payload = await _post_token_request(task.oauth_token_url, body)
        return _persist_token_response(task, db, payload)
    finally:
        lock.release()

"""Unit tests for OAuth2 token acquisition and refresh (P0-A)."""
import os

os.environ.setdefault("ENCRYPTION_KEY", "ancg5kTQFZYtqA3LyzV9MrixQ1HyC95gitaGyZ1nDPk=")

import asyncio
import datetime as _dt
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

import httpx
import pytest

from app.services import oauth_token_service
from app.core.encryption import decrypt_value, encrypt_value


def _make_task(**overrides):
    """A bare object that exposes the Task fields the service touches.

    SimpleNamespace is sufficient because oauth_token_service uses attribute
    access, not the full ORM. Encryption is real (Fernet).
    """
    base = dict(
        id=42,
        oauth_grant_type="client_credentials",
        oauth_token_url="https://idp.example.test/token",
        oauth_client_id="client-id",
        oauth_client_secret=encrypt_value("super-secret"),
        oauth_scope="read",
        oauth_audience=None,
        oauth_access_token=None,
        oauth_refresh_token=None,
        oauth_token_expires_at=None,
        oauth_config=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeDB:
    """Minimal Session stub matching the call surface of oauth_token_service."""

    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        # No-op for tests; real Session would re-read from DB.
        return obj


def _fake_async_client(response):
    """Return a context-manager mock whose .post() returns `response`."""

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None, headers=None):
            return response

    return _Ctx()


@pytest.mark.asyncio
async def test_client_credentials_fetch_persists_encrypted_token(monkeypatch):
    task = _make_task()
    db = _FakeDB()

    body = {"access_token": "ACCESS-1", "expires_in": 3600, "token_type": "Bearer"}
    response = httpx.Response(200, json=body, request=httpx.Request("POST", task.oauth_token_url))

    # Reset registry so this test's lock doesn't leak across tests.
    oauth_token_service._TASK_LOCKS.clear()

    with patch.object(httpx, "AsyncClient", lambda *a, **kw: _fake_async_client(response)):
        token = await oauth_token_service.get_access_token(task, db)

    assert token == "ACCESS-1"
    # Persisted encrypted, not plaintext
    assert task.oauth_access_token != "ACCESS-1"
    assert decrypt_value(task.oauth_access_token) == "ACCESS-1"
    assert task.oauth_token_expires_at is not None
    assert task.oauth_token_expires_at > _dt.datetime.now(_dt.timezone.utc)
    assert db.commits == 1


@pytest.mark.asyncio
async def test_token_reused_within_skew_no_new_post():
    """A cached, unexpired token must not trigger another HTTP call."""
    expires = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=600)
    task = _make_task(
        oauth_access_token=encrypt_value("CACHED-TOKEN"),
        oauth_token_expires_at=expires,
    )
    db = _FakeDB()
    oauth_token_service._TASK_LOCKS.clear()

    posts = []

    def _client(*args, **kwargs):
        # Should never be called
        posts.append((args, kwargs))
        raise AssertionError("HTTP token fetch should not happen for cached token")

    with patch.object(httpx, "AsyncClient", _client):
        token = await oauth_token_service.get_access_token(task, db)

    assert token == "CACHED-TOKEN"
    assert posts == []
    assert db.commits == 0  # No persistence on cache hit


@pytest.mark.asyncio
async def test_force_refresh_overrides_cache():
    """force_refresh=True must hit the token endpoint even if cache is valid."""
    expires = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=600)
    task = _make_task(
        oauth_access_token=encrypt_value("OLD-TOKEN"),
        oauth_token_expires_at=expires,
    )
    db = _FakeDB()
    oauth_token_service._TASK_LOCKS.clear()

    body = {"access_token": "NEW-TOKEN", "expires_in": 600}
    response = httpx.Response(200, json=body, request=httpx.Request("POST", task.oauth_token_url))

    with patch.object(httpx, "AsyncClient", lambda *a, **kw: _fake_async_client(response)):
        token = await oauth_token_service.get_access_token(task, db, force_refresh=True)

    assert token == "NEW-TOKEN"
    assert decrypt_value(task.oauth_access_token) == "NEW-TOKEN"


@pytest.mark.asyncio
async def test_static_grant_returns_cached_or_legacy_oauth_config():
    """`static` grant_type must read the access_token without making any HTTP call."""
    task = _make_task(
        oauth_grant_type="static",
        oauth_token_url=None,
        oauth_access_token=encrypt_value("STATIC-TOKEN"),
    )
    db = _FakeDB()
    oauth_token_service._TASK_LOCKS.clear()

    with patch.object(httpx, "AsyncClient", lambda *a, **kw: pytest.fail("should not POST")):
        token = await oauth_token_service.get_access_token(task, db)

    assert token == "STATIC-TOKEN"


def test_lock_registry_keyed_by_loop_id():
    """Regression: asyncio.Lock instances are loop-bound. The registry must key
    by (task_id, id(loop)) so successive Celery asyncio.run() invocations don't
    crash with "Lock is bound to a different event loop"."""
    oauth_token_service._TASK_LOCKS.clear()

    body = {"access_token": "T", "expires_in": 60}

    async def _one_shot(loop_id_holder):
        # Capture the lock keyed under this loop's id.
        task = _make_task()
        db = _FakeDB()
        response = httpx.Response(
            200, json=body, request=httpx.Request("POST", task.oauth_token_url)
        )
        with patch.object(httpx, "AsyncClient", lambda *a, **kw: _fake_async_client(response)):
            await oauth_token_service.get_access_token(task, db)
        loop_id_holder.append(id(asyncio.get_running_loop()))

    holder1 = []
    holder2 = []
    # Two distinct asyncio.run calls = two distinct event loops, mirroring
    # what Celery does between task invocations.
    asyncio.run(_one_shot(holder1))
    asyncio.run(_one_shot(holder2))

    assert holder1 and holder2 and holder1[0] != holder2[0]
    # Both invocations should have succeeded without "<Lock> is bound to a
    # different event loop" raising.


@pytest.mark.asyncio
async def test_refresh_token_grant_persists_rotated_refresh_token():
    """If the IdP returns a new refresh_token, it must be re-encrypted and persisted."""
    task = _make_task(
        oauth_grant_type="refresh_token",
        oauth_refresh_token=encrypt_value("OLD-REFRESH"),
    )
    db = _FakeDB()
    oauth_token_service._TASK_LOCKS.clear()

    body = {
        "access_token": "ACCESS-2",
        "expires_in": 60,
        "refresh_token": "NEW-REFRESH",
    }
    response = httpx.Response(200, json=body, request=httpx.Request("POST", task.oauth_token_url))

    with patch.object(httpx, "AsyncClient", lambda *a, **kw: _fake_async_client(response)):
        token = await oauth_token_service.get_access_token(task, db)

    assert token == "ACCESS-2"
    assert decrypt_value(task.oauth_refresh_token) == "NEW-REFRESH"

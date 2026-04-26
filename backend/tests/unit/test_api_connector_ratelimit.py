"""Unit tests for HTTP 429 / Retry-After handling in api_connector.fetch_json (P0-B)."""
import os

# Tests need a deterministic Fernet key for any code paths that touch encryption.
os.environ.setdefault("ENCRYPTION_KEY", "ancg5kTQFZYtqA3LyzV9MrixQ1HyC95gitaGyZ1nDPk=")

import datetime as _dt
import email.utils
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import pytest

from app.services import api_connector
from app.services.api_connector import _parse_retry_after, fetch_json


class TestParseRetryAfter:
    def test_integer_seconds(self):
        assert _parse_retry_after("5") == 5.0

    def test_zero_seconds(self):
        assert _parse_retry_after("0") == 0.0

    def test_negative_seconds_clamped_to_zero(self):
        assert _parse_retry_after("-3") == 0.0

    def test_http_date_future(self):
        future = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=10)
        header = email.utils.format_datetime(future)
        result = _parse_retry_after(header)
        assert result is not None
        # Allow generous slack for clock skew + parser delay.
        assert 5.0 <= result <= 15.0

    def test_http_date_past_clamped_to_zero(self):
        past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=60)
        header = email.utils.format_datetime(past)
        assert _parse_retry_after(header) == 0.0

    def test_unparseable_returns_none(self):
        assert _parse_retry_after("not-a-date") is None

    def test_none_returns_none(self):
        assert _parse_retry_after(None) is None


def _make_response(status: int, headers=None, json_payload=None):
    """Build an httpx.Response for use in mocked client.request side_effect."""
    return httpx.Response(
        status_code=status,
        headers=headers or {},
        json=json_payload if json_payload is not None else {"ok": True},
        request=httpx.Request("GET", "https://example.test/data"),
    )


class _SequencedClient:
    """Mock httpx.AsyncClient that returns a queued sequence of responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, *args, **kwargs):
        self.calls += 1
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_429_with_integer_retry_after_retries_and_succeeds():
    """A single 429 with Retry-After:1 should sleep ~1s and succeed on the next try."""
    sequence = [
        _make_response(429, headers={"Retry-After": "1"}),
        _make_response(200, json_payload={"data": "ok"}),
    ]
    sequenced = _SequencedClient(sequence)

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("app.services.api_connector.httpx.AsyncClient", return_value=sequenced), \
         patch("app.services.api_connector.asyncio.sleep", side_effect=fake_sleep):
        result = await fetch_json("GET", "https://example.test/data", max_retries=0)

    assert result == {"data": "ok"}
    assert sleep_calls == [1.0]
    assert sequenced.calls == 2


@pytest.mark.asyncio
async def test_429_http_date_retry_after_parsed_to_delta():
    """Retry-After as an HTTP-date should be converted to a delta seconds sleep."""
    future = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=2)
    header = email.utils.format_datetime(future)

    sequence = [
        _make_response(429, headers={"Retry-After": header}),
        _make_response(200, json_payload={"ok": True}),
    ]
    sequenced = _SequencedClient(sequence)
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("app.services.api_connector.httpx.AsyncClient", return_value=sequenced), \
         patch("app.services.api_connector.asyncio.sleep", side_effect=fake_sleep):
        result = await fetch_json("GET", "https://example.test/data", max_retries=0)

    assert result == {"ok": True}
    assert len(sleep_calls) == 1
    # Allow slack: parser converts to absolute then back to delta.
    assert 0.0 <= sleep_calls[0] <= 5.0


@pytest.mark.asyncio
async def test_429_wait_above_cap_raises_without_sleeping():
    """If Retry-After exceeds max_wait_seconds, request fails without blocking."""
    sequence = [_make_response(429, headers={"Retry-After": "9999"})]
    sequenced = _SequencedClient(sequence)
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("app.services.api_connector.httpx.AsyncClient", return_value=sequenced), \
         patch("app.services.api_connector.asyncio.sleep", side_effect=fake_sleep):
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_json(
                "GET",
                "https://example.test/data",
                max_retries=0,
                max_wait_seconds=10,
            )

    assert sleep_calls == []  # Never slept


@pytest.mark.asyncio
async def test_429_retries_exhausted_raises():
    """After max_retries_429 attempts, the request bubbles up the HTTPStatusError."""
    sequence = [
        _make_response(429, headers={"Retry-After": "0"}),
        _make_response(429, headers={"Retry-After": "0"}),
        _make_response(429, headers={"Retry-After": "0"}),
    ]
    sequenced = _SequencedClient(sequence)

    async def fake_sleep(_):
        return None

    with patch("app.services.api_connector.httpx.AsyncClient", return_value=sequenced), \
         patch("app.services.api_connector.asyncio.sleep", side_effect=fake_sleep):
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_json(
                "GET",
                "https://example.test/data",
                max_retries=0,
                max_retries_429=2,
            )

    assert sequenced.calls == 3  # initial + 2 retries

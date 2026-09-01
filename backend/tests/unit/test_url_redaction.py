"""Tests for the log-safe URL redaction helper."""

import pytest

from app.services.api_connector import _redact_url_for_log


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://api.example.com/v1/users?api_key=SECRET", "https://api.example.com/v1/users"),
        ("https://user:s3cret@api.example.com/v1/users", "https://api.example.com/v1/users"),
        ("https://api.example.com:8443/v1/users#frag", "https://api.example.com:8443/v1/users"),
        ("https://user:s3cret@[::1]:8080/p?x=1", "https://[::1]:8080/p"),
        ("https://api.example.com/v1/users", "https://api.example.com/v1/users"),
        (
            "https://api.example.com/v1;jsessionid=SECRET/users;v=2?x=1",
            "https://api.example.com/v1/users",
        ),
    ],
)
def test_query_userinfo_and_fragment_are_dropped(raw, expected):
    assert _redact_url_for_log(raw) == expected


def test_control_characters_cannot_forge_log_lines():
    forged = "https://api.example.com/v1\r\n2026-01-01 ERROR fake line?token=abc"
    redacted = _redact_url_for_log(forged)
    assert "\r" not in redacted and "\n" not in redacted
    assert "token" not in redacted

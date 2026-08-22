"""Tests for the SSRF url_guard (v1.4 C4)."""

import pytest

from app.core import url_guard
from app.core.url_guard import SSRFBlockedError, validate_url


class TestSchemeValidation:
    def test_rejects_non_http_schemes(self):
        for url in ("file:///etc/passwd", "ftp://example.com/x", "gopher://h/x"):
            with pytest.raises(SSRFBlockedError):
                validate_url(url, resolve=False)

    def test_rejects_empty_and_hostless(self):
        with pytest.raises(SSRFBlockedError):
            validate_url("", resolve=False)
        with pytest.raises(SSRFBlockedError):
            validate_url("https://", resolve=False)


class TestLiteralIpBlocking:
    def test_blocks_metadata_endpoint(self):
        with pytest.raises(SSRFBlockedError):
            validate_url("http://169.254.169.254/latest/meta-data/", resolve=False)

    def test_blocks_loopback(self):
        with pytest.raises(SSRFBlockedError):
            validate_url("http://127.0.0.1:6379/", resolve=False)

    def test_blocks_ipv6_loopback(self):
        with pytest.raises(SSRFBlockedError):
            validate_url("http://[::1]:6379/", resolve=False)

    def test_blocks_rfc1918(self):
        for host in ("10.0.0.5", "192.168.1.10", "172.16.0.1"):
            with pytest.raises(SSRFBlockedError):
                validate_url(f"http://{host}/", resolve=False)

    def test_allows_public_ip(self):
        assert validate_url("https://93.184.216.34/v1", resolve=False) == "https://93.184.216.34/v1"


class TestAllowlist:
    def test_allowlisted_private_host_passes_literal_check(self, monkeypatch):
        # Host-string match: an explicitly allowlisted (literal or resolved)
        # private address is permitted for legitimate internal sources.
        monkeypatch.setattr(url_guard.settings, "ALLOWED_SOURCE_HOSTS", "169.254.169.254")
        assert validate_url("http://169.254.169.254/", resolve=False) == "http://169.254.169.254/"

    def test_non_allowlisted_still_blocked(self, monkeypatch):
        monkeypatch.setattr(url_guard.settings, "ALLOWED_SOURCE_HOSTS", "other.internal")
        with pytest.raises(SSRFBlockedError):
            validate_url("http://127.0.0.1/", resolve=False)


class TestResolution:
    def test_unresolvable_host_blocked(self):
        with pytest.raises(SSRFBlockedError):
            validate_url("http://this-host-does-not-exist-9f3a2b.invalid/")

    def test_localhost_resolution_blocked(self):
        # localhost resolves to 127.0.0.1 in this environment
        with pytest.raises(SSRFBlockedError):
            validate_url("http://localhost:8000/")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

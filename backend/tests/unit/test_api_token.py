"""Tests for the shared API token dependency (v1.4 H1)."""

import pytest
from fastapi.testclient import TestClient

from app.core.auth import enforce_api_token_configured, verify_api_token


class TestVerifyApiToken:
    def test_no_token_configured_allows_all(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_TOKEN", None)
        assert verify_api_token(None) is True
        assert verify_api_token("anything") is True

    def test_correct_and_incorrect_tokens(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_TOKEN", "s3cret")
        assert verify_api_token("s3cret") is True
        assert verify_api_token(None) is False
        assert verify_api_token("wrong") is False


class TestStartupGuard:
    def test_production_without_token_refuses_startup(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "API_TOKEN", None)
        with pytest.raises(RuntimeError, match="API_TOKEN"):
            enforce_api_token_configured()

    def test_production_with_token_starts(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "API_TOKEN", "s3cret")
        enforce_api_token_configured()


class TestEndpointAuth:
    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

    def test_missing_token_rejected_when_configured(self, monkeypatch, client):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_TOKEN", "s3cret")
        resp = client.get("/api/v1/tasks/")
        assert resp.status_code == 401

    def test_wrong_token_rejected(self, monkeypatch, client):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_TOKEN", "s3cret")
        resp = client.get("/api/v1/tasks/", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

    def test_bearer_header_accepted(self, monkeypatch, client):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_TOKEN", "s3cret")
        resp = client.get("/api/v1/tasks/", headers={"Authorization": "Bearer s3cret"})
        assert resp.status_code == 200

    def test_x_api_key_accepted(self, monkeypatch, client):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_TOKEN", "s3cret")
        resp = client.get("/api/v1/tasks/", headers={"X-API-Key": "s3cret"})
        assert resp.status_code == 200

    def test_health_endpoint_open(self, monkeypatch, client):
        """/health stays unauthenticated for load-balancer probes."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_TOKEN", "s3cret")
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_open_access_when_unconfigured(self, monkeypatch, client):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_TOKEN", None)
        resp = client.get("/api/v1/tasks/")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

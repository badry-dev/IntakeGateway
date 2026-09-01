"""Tests for environment normalization and docs gating (v1.4 review)."""

import pytest

from app.core.config import Settings


class TestAppEnvNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("dev", "dev"),
            ("Production", "production"),
            ("  PRODUCTION  ", "production"),
            ("Dev", "dev"),
        ],
    )
    def test_app_env_normalized(self, raw, expected):
        settings = Settings(APP_ENV=raw, SECRET_KEY="x")
        assert settings.APP_ENV == expected

    def test_missing_app_env_defaults_to_dev(self):
        # Missing APP_ENV falls back to the dev default: interactive docs
        # stay enabled outside production by design.
        import os

        env = {k: v for k, v in os.environ.items() if k != "APP_ENV"}
        import subprocess
        import sys
        from pathlib import Path

        backend = Path(__file__).resolve().parents[2]
        code = "from app.core.config import Settings;print(Settings(SECRET_KEY='x').APP_ENV)"
        out = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            cwd=str(backend),
            capture_output=True,
            text=True,
        )
        assert out.stdout.strip() == "dev"


class TestDocsGating:
    def _make_app(self, app_env):
        import importlib

        from app.core.config import settings

        original = settings.APP_ENV
        original_token = settings.API_TOKEN
        settings.APP_ENV = app_env
        # Production fail-closed guard requires a token at import time.
        if app_env == "production":
            settings.API_TOKEN = "test-token"
        try:
            import app.main as main_module

            importlib.reload(main_module)
            return main_module.app
        finally:
            settings.APP_ENV = original
            settings.API_TOKEN = original_token

    def test_docs_enabled_outside_production(self):
        from fastapi.testclient import TestClient

        app = self._make_app("dev")
        client = TestClient(app)
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200

    def test_docs_disabled_in_production_canonical_value(self):
        from fastapi.testclient import TestClient

        app = self._make_app("production")
        client = TestClient(app)
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404

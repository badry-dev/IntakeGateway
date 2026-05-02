"""Unit tests for cursor / backfill / replay semantics in runner.run_import (P0-C)."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "ancg5kTQFZYtqA3LyzV9MrixQ1HyC95gitaGyZ1nDPk=")

from unittest.mock import MagicMock, patch

import pytest

from app.services import runner


def test_cursor_param_name_invalid_pattern_raises():
    """Cursor identifiers must match the safe-identifier whitelist."""
    invalid_names = ["foo bar", "a&b", "with=equals", "?weird", "../etc"]
    for name in invalid_names:
        assert not runner._SAFE_IDENTIFIER_RE.match(name), name


def test_cursor_param_name_valid_pattern_passes():
    valid_names = ["since", "updated_at", "Cursor1", "_cursor", "x_y_z123"]
    for name in valid_names:
        assert runner._SAFE_IDENTIFIER_RE.match(name), name


@pytest.mark.asyncio
async def test_replay_refused_when_upsert_disabled_and_not_forced():
    """A replay against a non-upsert task with force=False must be refused."""

    fake_task = MagicMock()
    fake_task.is_active = True
    fake_task.connection_id = "conn-1"
    fake_task.upsert_enabled = False
    fake_task.cursor_field = None
    fake_task.cursor_param_name = None

    fake_db = MagicMock()
    fake_db.get.return_value = fake_task

    with patch.object(runner, "set_task_context"), patch.object(runner, "clear_task_context"):
        with pytest.raises(ValueError, match="Replay refused"):
            await runner.run_import(
                task_id=1,
                db=fake_db,
                replay_of_run_id=99,
                force_replay=False,
            )


@pytest.mark.asyncio
async def test_invalid_cursor_param_name_raises_before_run_creation():
    """Bad cursor_param_name must fail fast (before any TaskRun is committed)."""
    fake_task = MagicMock()
    fake_task.is_active = True
    fake_task.connection_id = "conn-1"
    fake_task.upsert_enabled = True
    fake_task.cursor_field = "updated_at"
    fake_task.cursor_param_name = "bad name with spaces"

    fake_db = MagicMock()
    fake_db.get.return_value = fake_task

    with patch.object(runner, "set_task_context"), patch.object(runner, "clear_task_context"):
        with pytest.raises(ValueError, match="cursor_param_name"):
            await runner.run_import(task_id=1, db=fake_db)


@pytest.mark.asyncio
async def test_invalid_cursor_field_raises():
    fake_task = MagicMock()
    fake_task.is_active = True
    fake_task.connection_id = "conn-1"
    fake_task.upsert_enabled = True
    fake_task.cursor_field = "bad field"  # space is invalid
    fake_task.cursor_param_name = "since"

    fake_db = MagicMock()
    fake_db.get.return_value = fake_task

    with patch.object(runner, "set_task_context"), patch.object(runner, "clear_task_context"):
        with pytest.raises(ValueError, match="cursor_field"):
            await runner.run_import(task_id=1, db=fake_db)

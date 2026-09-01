"""Regression tests for scheduler dispatch (v1.4 C1).

The scheduled-job handler used to call ``enqueue_run.delay(task_id)``, but
``enqueue_run`` is a plain function that already delegates to
``run_import_task.delay()`` — so every cron fire raised AttributeError,
swallowed by the broad except. These tests pin the corrected dispatch and the
consecutive-failure counter behavior.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.db.models.task_schedule import TaskSchedule
from app.services.scheduler import TaskScheduler


@pytest.fixture
def scheduler():
    with patch("app.services.scheduler.SessionLocal") as mock_session_local:
        db = MagicMock()
        mock_session_local.return_value = db
        sched = TaskScheduler()
        sched.db = db
        yield sched, db


def _make_schedule(consecutive_failures=0, is_active=True):
    schedule = MagicMock(spec=TaskSchedule)
    schedule.task_id = 7
    schedule.cron_expression = "0 2 * * *"
    schedule.consecutive_failures = consecutive_failures
    schedule.is_active = is_active
    schedule.last_run_date = None
    schedule.next_run_date = None
    return schedule


class TestScheduledDispatch:
    def test_dispatch_invokes_enqueue_run(self, scheduler):
        """The cron fire must call enqueue_run(task_id) — which itself invokes
        run_import_task.delay — not enqueue_run.delay (AttributeError)."""
        sched, db = scheduler

        schedule = _make_schedule(consecutive_failures=2)
        db.query.return_value.filter.return_value.first.return_value = schedule

        with patch("app.services.scheduler.enqueue_run") as mock_enqueue:
            mock_enqueue.return_value = MagicMock(id="celery-id-1")
            sched._execute_scheduled_task(7, "Nightly import")

        mock_enqueue.assert_called_once_with(7)
        # Successful dispatch resets the failure counter
        assert schedule.consecutive_failures == 0

    def test_dispatch_updates_schedule_dates_on_success(self, scheduler):
        sched, db = scheduler

        schedule = _make_schedule()
        db.query.return_value.filter.return_value.first.return_value = schedule

        with patch("app.services.scheduler.enqueue_run") as mock_enqueue:
            mock_enqueue.return_value = MagicMock(id="celery-id-2")
            sched._execute_scheduled_task(7, "Nightly import")

        assert schedule.last_run_date is not None
        assert schedule.next_run_date is not None
        db.commit.assert_called()


class TestDispatchFailureCounter:
    def test_failure_counter_persists_when_enqueue_raises(self, scheduler):
        """On enqueue failure the counter is incremented and committed in a
        separate transaction AFTER the rollback."""
        sched, db = scheduler

        schedule = _make_schedule(consecutive_failures=2)
        db.query.return_value.filter.return_value.first.return_value = schedule

        with patch("app.services.scheduler.enqueue_run", side_effect=RuntimeError("broker down")):
            sched._execute_scheduled_task(7, "Nightly import")

        # Rollback happens first (discarding pre-error state)...
        db.rollback.assert_called_once()
        # ...then the counter is incremented in a fresh transaction.
        assert schedule.consecutive_failures == 3
        assert db.commit.call_count >= 1

    def test_failure_without_schedule_row_does_not_crash(self, scheduler):
        """No matching TaskSchedule row -> counter step is skipped safely."""
        sched, db = scheduler
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.scheduler.enqueue_run", side_effect=RuntimeError("broker down")):
            sched._execute_scheduled_task(7, "Nightly import")

        db.rollback.assert_called()

    def test_counter_commit_failure_is_swallowed(self, scheduler):
        """A failure while persisting the counter must not escape the handler
        (it would make APScheduler mark the job as errored)."""
        sched, db = scheduler
        schedule = _make_schedule(consecutive_failures=1)
        db.query.return_value.filter.return_value.first.return_value = schedule
        db.commit.side_effect = RuntimeError("db gone")

        with patch("app.services.scheduler.enqueue_run", side_effect=RuntimeError("broker down")):
            # Must not raise
            sched._execute_scheduled_task(7, "Nightly import")

    def test_bookkeeping_failure_does_not_count_as_dispatch_failure(self, scheduler):
        """A failure AFTER a successful enqueue (e.g. metadata commit) must not
        increment consecutive_failures — Celery already accepted the job."""
        sched, db = scheduler
        schedule = _make_schedule(consecutive_failures=4)
        db.query.return_value.filter.return_value.first.return_value = schedule
        db.commit.side_effect = RuntimeError("sqlite locked")

        with (
            patch("app.services.scheduler.enqueue_run") as mock_enqueue,
            patch.object(sched, "_handle_dispatch_failure") as mock_handle,
        ):
            mock_enqueue.return_value = MagicMock(id="celery-id-3")
            sched._execute_scheduled_task(7, "Nightly import")

        # Dispatch succeeded; the metadata failure is handled separately and
        # must NOT be recorded as a dispatch failure.
        mock_enqueue.assert_called_once()
        mock_handle.assert_not_called()
        db.rollback.assert_called_once()

    def test_auto_pause_at_threshold_deactivates_schedule(self, scheduler):
        """Reaching the consecutive-failure threshold deactivates the schedule
        and removes its APScheduler job."""
        sched, db = scheduler
        schedule = _make_schedule(consecutive_failures=4, is_active=True)
        db.query.return_value.filter.return_value.first.return_value = schedule

        with (
            patch("app.services.scheduler.enqueue_run", side_effect=RuntimeError("down")),
            patch.object(sched, "remove_schedule") as mock_remove,
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_settings.SCHEDULE_MAX_CONSECUTIVE_FAILURES = 5
            sched._execute_scheduled_task(7, "Nightly import")

        assert schedule.is_active is False
        assert schedule.consecutive_failures == 5
        mock_remove.assert_called_once_with(7)

    def test_below_threshold_does_not_pause(self, scheduler):
        sched, db = scheduler
        schedule = _make_schedule(consecutive_failures=1, is_active=True)
        db.query.return_value.filter.return_value.first.return_value = schedule

        with (
            patch("app.services.scheduler.enqueue_run", side_effect=RuntimeError("down")),
            patch.object(sched, "remove_schedule") as mock_remove,
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_settings.SCHEDULE_MAX_CONSECUTIVE_FAILURES = 5
            sched._execute_scheduled_task(7, "Nightly import")

        assert schedule.is_active is True
        mock_remove.assert_not_called()

    def test_auto_pause_is_persisted_before_the_job_is_removed(self, scheduler):
        """If the commit failed after the job was gone, the DB would still say
        active while nothing dispatches — so the order must be commit, then remove."""
        sched, db = scheduler
        schedule = _make_schedule(consecutive_failures=4, is_active=True)
        db.query.return_value.filter.return_value.first.return_value = schedule
        order: list[str] = []
        db.commit.side_effect = lambda: order.append("commit")

        with (
            patch("app.services.scheduler.enqueue_run", side_effect=RuntimeError("down")),
            patch.object(sched, "remove_schedule", side_effect=lambda tid: order.append("remove")),
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_settings.SCHEDULE_MAX_CONSECUTIVE_FAILURES = 5
            sched._execute_scheduled_task(7, "Nightly import")

        assert order == ["commit", "remove"]
        assert schedule.is_active is False

    def test_job_removal_failure_keeps_the_persisted_pause(self, scheduler):
        sched, db = scheduler
        schedule = _make_schedule(consecutive_failures=4, is_active=True)
        db.query.return_value.filter.return_value.first.return_value = schedule

        with (
            patch("app.services.scheduler.enqueue_run", side_effect=RuntimeError("down")),
            patch.object(sched, "remove_schedule", side_effect=RuntimeError("apscheduler gone")),
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_settings.SCHEDULE_MAX_CONSECUTIVE_FAILURES = 5
            sched._execute_scheduled_task(7, "Nightly import")  # must not raise

        assert schedule.is_active is False
        db.commit.assert_called_once()
        # Only the initial rollback that precedes the counter transaction.
        db.rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

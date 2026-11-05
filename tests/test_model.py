"""
Integration tests for PendingDatasetEvent: they need the test Postgres database (db_session_for_testing).
"""
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import sessionmaker

from common.model import FLUSH_LOCK_KEY, PendingDatasetEvent

QUIET = 300
MAX_WAIT = 1800


def _add(session, dataset_id, age_seconds, event_type='resource-created'):
    """Inserts a pending event that was received `age_seconds` ago (by the database clock)."""
    PendingDatasetEvent.add(session, dataset_id, {'event_type': event_type, 'dataset_id': dataset_id})
    session.flush()
    session.execute(
        update(PendingDatasetEvent)
        .where(PendingDatasetEvent.id == select(func.max(PendingDatasetEvent.id)).scalar_subquery())
        .values(received_at=func.now() - timedelta(seconds=age_seconds))
    )
    session.commit()


def _pending_dataset_ids(session):
    return sorted(session.execute(select(PendingDatasetEvent.dataset_id)).scalars())


def _other_session(session):
    return sessionmaker(bind=session.get_bind())()


class TestClaimDue:
    """DATASET_NOTIFICATIONS-011, -012, -014"""

    def test_add_stores_the_event_with_the_database_time(self, db_session_for_testing):
        PendingDatasetEvent.add(db_session_for_testing, 'dataset-1', {'event_type': 'resource-created'})
        db_session_for_testing.commit()

        row = db_session_for_testing.execute(select(PendingDatasetEvent)).scalar_one()
        assert row.dataset_id == 'dataset-1'
        assert row.event == {'event_type': 'resource-created'}
        assert row.received_at is not None

    def test_not_due_before_the_quiet_period(self, db_session_for_testing):
        _add(db_session_for_testing, 'dataset-1', age_seconds=QUIET - 60)

        assert PendingDatasetEvent.claim_due(db_session_for_testing, QUIET, MAX_WAIT) == []
        db_session_for_testing.commit()
        assert _pending_dataset_ids(db_session_for_testing) == ['dataset-1']

    def test_due_after_the_quiet_period(self, db_session_for_testing):
        _add(db_session_for_testing, 'dataset-1', age_seconds=QUIET + 60)
        _add(db_session_for_testing, 'dataset-1', age_seconds=QUIET + 10)

        claimed = PendingDatasetEvent.claim_due(db_session_for_testing, QUIET, MAX_WAIT)
        db_session_for_testing.commit()

        assert [row.dataset_id for row in claimed] == ['dataset-1', 'dataset-1']
        assert _pending_dataset_ids(db_session_for_testing) == []

    def test_a_recent_event_keeps_the_whole_dataset_waiting(self, db_session_for_testing):
        _add(db_session_for_testing, 'dataset-1', age_seconds=QUIET + 60)
        _add(db_session_for_testing, 'dataset-1', age_seconds=10)

        assert PendingDatasetEvent.claim_due(db_session_for_testing, QUIET, MAX_WAIT) == []

    def test_due_after_the_max_wait_even_with_recent_events(self, db_session_for_testing):
        _add(db_session_for_testing, 'dataset-1', age_seconds=MAX_WAIT + 60)
        _add(db_session_for_testing, 'dataset-1', age_seconds=10)

        claimed = PendingDatasetEvent.claim_due(db_session_for_testing, QUIET, MAX_WAIT)

        assert len(claimed) == 2

    def test_only_due_datasets_are_claimed(self, db_session_for_testing):
        _add(db_session_for_testing, 'dataset-due', age_seconds=QUIET + 60)
        _add(db_session_for_testing, 'dataset-waiting', age_seconds=10)

        claimed = PendingDatasetEvent.claim_due(db_session_for_testing, QUIET, MAX_WAIT)
        db_session_for_testing.commit()

        assert [row.dataset_id for row in claimed] == ['dataset-due']
        assert _pending_dataset_ids(db_session_for_testing) == ['dataset-waiting']

    def test_returns_none_without_waiting_when_the_lock_is_held(self, db_session_for_testing):
        _add(db_session_for_testing, 'dataset-1', age_seconds=QUIET + 60)
        other = _other_session(db_session_for_testing)
        try:
            assert other.execute(select(func.pg_try_advisory_xact_lock(FLUSH_LOCK_KEY))).scalar() is True

            assert PendingDatasetEvent.claim_due(db_session_for_testing, QUIET, MAX_WAIT) is None
            db_session_for_testing.rollback()
            assert _pending_dataset_ids(db_session_for_testing) == ['dataset-1']
        finally:
            other.rollback()
            other.close()

    def test_lock_is_released_by_commit(self, db_session_for_testing):
        _add(db_session_for_testing, 'dataset-1', age_seconds=QUIET + 60)
        other = _other_session(db_session_for_testing)
        try:
            assert PendingDatasetEvent.claim_due(other, QUIET, MAX_WAIT) is not None
            other.commit()

            assert PendingDatasetEvent.claim_due(db_session_for_testing, QUIET, MAX_WAIT) == []
        finally:
            other.close()

    def test_inserts_are_not_blocked_by_a_claim_in_progress(self, db_session_for_testing):
        """An event stored while another instance's claim is open stays pending for the next group (P1)."""
        _add(db_session_for_testing, 'dataset-1', age_seconds=QUIET + 60)
        other = _other_session(db_session_for_testing)
        try:
            claimed = PendingDatasetEvent.claim_due(other, QUIET, MAX_WAIT)

            PendingDatasetEvent.add(db_session_for_testing, 'dataset-1', {'event_type': 'resource-data-changed'})
            db_session_for_testing.commit()

            other.commit()
        finally:
            other.close()

        assert len(claimed) == 1
        remaining = db_session_for_testing.execute(select(PendingDatasetEvent.event)).scalars().all()
        assert remaining == [{'event_type': 'resource-data-changed'}]


class TestGetPendingStats:
    """DATASET_NOTIFICATIONS-023"""

    def test_empty(self, db_session_for_testing):
        assert PendingDatasetEvent.get_pending_stats(db_session_for_testing) == (0, None)

    def test_count_and_oldest_age(self, db_session_for_testing):
        _add(db_session_for_testing, 'dataset-1', age_seconds=120)
        _add(db_session_for_testing, 'dataset-2', age_seconds=10)

        count, oldest_age = PendingDatasetEvent.get_pending_stats(db_session_for_testing)

        assert count == 2
        assert timedelta(seconds=119) < oldest_age < timedelta(seconds=180)

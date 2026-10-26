import datetime
import json
from collections import namedtuple
from unittest.mock import MagicMock, patch

import pytest

from config.config import get_config
from listener_processing.aggregation import buffer_dataset_event, build_aggregated_payload, flush_due_dataset_events
from listener_processing.helpers import EVENT_TYPE_RESOURCE_CREATED, EVENT_TYPE_RESOURCE_DATA_CHANGED, \
    EVENT_TYPE_RESOURCE_DELETED

Row = namedtuple('Row', ['id', 'dataset_id', 'event', 'received_at'])


def _event(event_type, resource_id, event_time, dataset_id='dataset-1', **extra):
    event = {
        'event_type': event_type,
        'event_time': event_time,
        'event_source': 'ckan',
        'initiator_user_name': 'example-bot',
        'dataset_id': dataset_id,
        'dataset_name': f'{dataset_id}-name',
        'dataset_title': f'{dataset_id} title',
        'org_id': 'org-1',
        'org_name': 'example-org',
        'org_title': 'Example Organisation',
        'resource_id': resource_id,
        'resource_name': f'{resource_id}.csv',
        'changed_fields': [{'field': 'last_modified', 'old_value': 'a', 'new_value': 'b'}],
    }
    event.update(extra)
    return event


def _rows(*events):
    return [Row(i, e['dataset_id'], e, None) for i, e in enumerate(events, start=1)]


def _sent_payloads(mock_requests):
    return [json.loads(call.kwargs['data']) for call in mock_requests.call_args_list]


def test_buffer_dataset_event_adds_and_commits():
    session = MagicMock()
    with patch('listener_processing.aggregation.PendingDatasetEvent.add') as mock_add:
        buffer_dataset_event(session, 'dataset-1', {'event_type': EVENT_TYPE_RESOURCE_CREATED})
    mock_add.assert_called_once_with(session, 'dataset-1', {'event_type': EVENT_TYPE_RESOURCE_CREATED})
    session.commit.assert_called_once()


def test_build_aggregated_payload():
    """DATASET_NOTIFICATIONS-020"""
    first = _event(EVENT_TYPE_RESOURCE_CREATED, 'r1', '2026-10-04T08:00:01.501234', dataset_title='Old title')
    last = _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r2', '2026-10-04T08:00:08.020511', dataset_title='New title')
    changes = [{'email_event_type': EVENT_TYPE_RESOURCE_CREATED, 'resource_name': 'r1.csv', 'resource_id': 'r1'}]

    payload = build_aggregated_payload('a1b2-c3d4', [first, last], changes)

    assert payload == {
        'event': {
            'dataset_name': 'dataset-1-name',
            'dataset_title': 'New title',
            'org_title': 'Example Organisation',
            'org_name': 'example-org',
            'org_id': 'org-1',
            'dataset_id': 'dataset-1',
            'initiator_user_name': 'example-bot',
            'event_time': '2026-10-04T08:00:01.501234',
        },
        'changes': changes,
        'hdx_url': get_config().HDX_URL,
        'unsubscribe_token_key': 'unsubscribe_token_a1b2_c3d4',
        'dataset_id': 'a1b2-c3d4',
    }


@pytest.fixture
def mock_pending_stats():
    with patch('listener_processing.aggregation.PendingDatasetEvent.get_pending_stats',
               return_value=(0, None)) as mock_stats:
        yield mock_stats


class TestFlushDueDatasetEvents:

    @patch('requests.request')
    @patch('listener_processing.aggregation.Subscription.get_users_subscribed_to_object')
    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due')
    def test_one_trigger_per_subscriber_per_dataset(self, mock_claim, mock_subscribers, mock_requests,
                                                    mock_pending_stats):
        """DATASET_NOTIFICATIONS-016, -020, -021"""
        mock_claim.return_value = _rows(
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', '2026-10-04T08:00:01'),
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r2', '2026-10-04T08:00:01'),
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', '2026-10-04T08:00:08'),
        )
        mock_subscribers.return_value = ['user-1', 'user-2']
        session = MagicMock()

        flush_due_dataset_events(session)

        assert mock_requests.call_count == 2
        payloads = _sent_payloads(mock_requests)
        assert [p['to']['subscriberId'] for p in payloads] == ['user-1', 'user-2']
        for p in payloads:
            assert p['name'] == 'dataset-notification-v3'
            assert 'transactionId' not in p
            assert [c['resource_id'] for c in p['payload']['changes']] == ['r1', 'r2']
        mock_subscribers.assert_called_once_with(session, 'dataset', 'dataset-1')
        session.close.assert_called_once()

    @patch('requests.request')
    @patch('listener_processing.aggregation.Subscription.get_users_subscribed_to_object')
    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due')
    def test_claim_is_committed_before_sending(self, mock_claim, mock_subscribers, mock_requests,
                                               mock_pending_stats):
        """DATASET_NOTIFICATIONS-014, -015"""
        calls = []
        session = MagicMock()
        session.commit.side_effect = lambda: calls.append('commit')
        mock_requests.side_effect = lambda *args, **kwargs: calls.append('request')
        mock_claim.return_value = _rows(_event(EVENT_TYPE_RESOURCE_CREATED, 'r1', '2026-10-04T08:00:01'))
        mock_subscribers.return_value = ['user-1']

        flush_due_dataset_events(session)

        assert calls.index('commit') < calls.index('request')

    @patch('requests.request')
    @patch('listener_processing.aggregation.Subscription.get_users_subscribed_to_object')
    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due')
    def test_events_are_ordered_by_event_time(self, mock_claim, mock_subscribers, mock_requests,
                                              mock_pending_stats):
        """The row ids come from 3 parallel listeners, so they don't give the event order (-017)."""
        deleted = _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', '2026-10-04T08:00:08')
        changed = _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', '2026-10-04T08:00:01')
        mock_claim.return_value = _rows(deleted, changed)
        mock_subscribers.return_value = ['user-1']

        flush_due_dataset_events(MagicMock())

        payload = _sent_payloads(mock_requests)[0]['payload']
        assert payload['changes'] == [
            {'email_event_type': EVENT_TYPE_RESOURCE_DELETED, 'resource_name': 'r1.csv', 'resource_id': 'r1'},
        ]
        assert payload['event']['event_time'] == '2026-10-04T08:00:01'

    @patch('requests.request')
    @patch('listener_processing.aggregation.Subscription.get_users_subscribed_to_object')
    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due')
    def test_separate_triggers_per_dataset(self, mock_claim, mock_subscribers, mock_requests, mock_pending_stats):
        mock_claim.return_value = _rows(
            _event(EVENT_TYPE_RESOURCE_CREATED, 'r1', '2026-10-04T08:00:01', dataset_id='dataset-1'),
            _event(EVENT_TYPE_RESOURCE_CREATED, 'r2', '2026-10-04T08:00:01', dataset_id='dataset-2'),
        )
        mock_subscribers.return_value = ['user-1']

        flush_due_dataset_events(MagicMock())

        assert sorted(p['payload']['dataset_id'] for p in _sent_payloads(mock_requests)) == ['dataset-1', 'dataset-2']

    @patch('requests.request')
    @patch('listener_processing.aggregation.Subscription.get_users_subscribed_to_object')
    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due')
    def test_nothing_sent_when_changes_are_empty(self, mock_claim, mock_subscribers, mock_requests,
                                                 mock_pending_stats):
        """DATASET_NOTIFICATIONS-019"""
        mock_claim.return_value = _rows(
            _event(EVENT_TYPE_RESOURCE_CREATED, 'r1', '2026-10-04T08:00:01'),
            _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', '2026-10-04T08:00:08'),
        )

        flush_due_dataset_events(MagicMock())

        mock_subscribers.assert_not_called()
        mock_requests.assert_not_called()

    @patch('requests.request')
    @patch('listener_processing.aggregation.Subscription.get_users_subscribed_to_object')
    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due')
    def test_nothing_sent_without_subscribers(self, mock_claim, mock_subscribers, mock_requests,
                                              mock_pending_stats):
        mock_claim.return_value = _rows(_event(EVENT_TYPE_RESOURCE_CREATED, 'r1', '2026-10-04T08:00:01'))
        mock_subscribers.return_value = []

        flush_due_dataset_events(MagicMock())

        mock_requests.assert_not_called()

    @patch('requests.request')
    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due', return_value=None)
    def test_skips_when_another_instance_holds_the_lock(self, mock_claim, mock_requests, mock_pending_stats):
        """DATASET_NOTIFICATIONS-014"""
        session = MagicMock()

        flush_due_dataset_events(session)

        mock_requests.assert_not_called()
        mock_pending_stats.assert_not_called()
        session.close.assert_called_once()

    @patch('requests.request')
    @patch('listener_processing.aggregation.Subscription.get_users_subscribed_to_object')
    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due')
    def test_failure_for_one_dataset_does_not_stop_the_others(self, mock_claim, mock_subscribers, mock_requests,
                                                              mock_pending_stats):
        """DATASET_NOTIFICATIONS-016"""
        mock_claim.return_value = _rows(
            _event(EVENT_TYPE_RESOURCE_CREATED, 'r1', '2026-10-04T08:00:01', dataset_id='dataset-1'),
            _event(EVENT_TYPE_RESOURCE_CREATED, 'r2', '2026-10-04T08:00:01', dataset_id='dataset-2'),
        )
        mock_subscribers.side_effect = [Exception('db error'), ['user-1']]
        session = MagicMock()

        flush_due_dataset_events(session)

        assert [p['payload']['dataset_id'] for p in _sent_payloads(mock_requests)] == ['dataset-2']
        session.rollback.assert_called_once()

    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due', side_effect=Exception('db down'))
    def test_claim_error_is_rolled_back_and_raised(self, mock_claim, mock_pending_stats):
        session = MagicMock()

        with pytest.raises(Exception, match='db down'):
            flush_due_dataset_events(session)

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch('listener_processing.aggregation.PendingDatasetEvent.claim_due', return_value=[])
    def test_logs_pending_stats(self, mock_claim, mock_pending_stats, caplog):
        """DATASET_NOTIFICATIONS-023"""
        mock_pending_stats.return_value = (7, datetime.timedelta(minutes=3))

        with caplog.at_level('INFO'):
            flush_due_dataset_events(MagicMock())

        assert 'Flushed 0 pending dataset events for 0 datasets; 7 still pending, oldest 0:03:00' in caplog.text

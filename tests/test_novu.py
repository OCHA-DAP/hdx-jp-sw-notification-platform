import json
from unittest.mock import patch

import pytest
import requests

from listener_processing.novu import NOVU_REQUEST_TIMEOUT, push_collection_notification_to_user, \
    push_dataset_notification_to_user, push_notification_to_novu, send_notifications_to_users


class TestNovuRequests:
    """DATASET_NOTIFICATIONS-027"""

    def test_timeout_is_connect_10s_read_60s(self):
        assert NOVU_REQUEST_TIMEOUT == (10, 60)

    @pytest.mark.parametrize('push', [
        lambda: push_dataset_notification_to_user('user-1', {'dataset_id': 'dataset-1'}),
        lambda: push_collection_notification_to_user('user-1', {'object_id': 'org-1'}),
        lambda: push_notification_to_novu({'event': {'dataset_id': 'dataset-1'}}),
    ])
    @patch('requests.request')
    def test_every_request_has_the_timeout(self, mock_requests, push):
        push()
        assert mock_requests.call_args.kwargs['timeout'] == NOVU_REQUEST_TIMEOUT

    @patch('requests.request', side_effect=requests.exceptions.ReadTimeout('read timed out'))
    def test_timeout_is_logged_and_dropped(self, mock_requests, caplog):
        push_dataset_notification_to_user('user-1', {'dataset_id': 'dataset-1'})

        assert mock_requests.call_count == 1
        assert 'Failed to send dataset notification to user user-1' in caplog.text


class TestWorkflowId:

    @patch('requests.request')
    def test_dataset_notifications_default_to_v2(self, mock_requests):
        send_notifications_to_users(['user-1'], {'dataset_id': 'dataset-1'})
        assert json.loads(mock_requests.call_args.kwargs['data'])['name'] == 'dataset-notification-v2'

    @patch('requests.request')
    def test_dataset_workflow_id_is_passed_through(self, mock_requests):
        send_notifications_to_users(['user-1', 'user-2'], {'dataset_id': 'dataset-1'},
                                    dataset_workflow_id='dataset-notification-v3')
        names = [json.loads(call.kwargs['data'])['name'] for call in mock_requests.call_args_list]
        assert names == ['dataset-notification-v3', 'dataset-notification-v3']

    @patch('requests.request')
    def test_collection_notifications_ignore_dataset_workflow_id(self, mock_requests):
        send_notifications_to_users(['user-1'], {'object_id': 'org-1'}, is_collection_event=True,
                                    dataset_workflow_id='dataset-notification-v3')
        assert json.loads(mock_requests.call_args.kwargs['data'])['name'] == 'dataset-collection-notification'

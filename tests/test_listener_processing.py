import uuid
import pytest
import json
from mock import patch

from common.model import NotifyObject, Subscription
from listener_processing.main import process, _handle_collection_event, _handle_dataset_event
from listener_processing.helpers import EVENT_TYPE_ORG_DATASET_ADDED, EVENT_TYPE_RESOURCE_CREATED


@pytest.fixture
def mock_objects_with_notifications():
    """Mock objects with notifications enabled"""
    return {'dataset_test-dataset-123', 'organization_test-org-789'}


@pytest.fixture
def mock_objects_without_notifications():
    """Mock objects without notifications"""
    return set()

@pytest.fixture
def sample_dataset_event():
    """Create a sample dataset event for testing"""
    from listener_processing.helpers import EVENT_TYPE_RESOURCE_CREATED
    return {
        'event_type': EVENT_TYPE_RESOURCE_CREATED,
        'event_time': '2024-10-02T11:22:15.973707',
        'event_source': 'ckan',
        'initiator_user_name': 'test_username',
        'dataset_name': 'test-dataset-123-name',
        'dataset_title': 'Test Dataset 123 Title',
        'dataset_id': 'test-dataset-123',
        'resource_name': 'test-file.csv',
        'resource_id': 'resource-456',
        'changed_fields': [],
    }

@pytest.fixture
def sample_collection_event():
    """Create a sample collection event for testing"""
    from listener_processing.helpers import EVENT_TYPE_ORG_DATASET_ADDED
    return {
        'event_type': EVENT_TYPE_ORG_DATASET_ADDED,
        'event_time': '2024-10-02T11:22:15.973707',
        'event_source': 'ckan',
        'object_id': 'test-org-789',
        'object_type': 'organization',
        'added_datasets': ['dataset-1', 'dataset-2', 'dataset-3'],
        'object_name': 'Test Organization'
    }


def create_test_data(session):
    """Helper function to create test data in the database"""
    # Create dataset object and subscription
    dataset_object = NotifyObject(type='dataset', hdx_id='test-dataset-123')
    session.add(dataset_object)
    session.flush()

    dataset_subscription = Subscription(
        subscription_id=uuid.uuid4(),
        user_id='user-dataset-123',
        event_type='dataset-updated',
        notify_object_id=dataset_object.id
    )
    session.add(dataset_subscription)

    # Create organization object and subscription
    org_object = NotifyObject(type='organization', hdx_id='test-org-789')
    session.add(org_object)
    session.flush()

    org_subscription = Subscription(
        subscription_id=uuid.uuid4(),
        user_id='user-org-456',
        event_type='dataset-updated',
        notify_object_id=org_object.id
    )
    session.add(org_subscription)

    session.commit()
    return dataset_object, org_object, dataset_subscription, org_subscription


class TestListenerProcessing:
    """Test suite for listener processing logic"""

    @patch('listener_processing.main.db_session')
    @patch('requests.request')
    def test_process_dataset_event_with_subscribers(
        self,
        mock_requests,
        mock_db_session,
        db_session_for_testing,
        sample_dataset_event,
        mock_objects_with_notifications,
        mock_objects_without_notifications
    ):
        """Test processing dataset event with subscribers"""
        # Setup
        mock_db_session.return_value = db_session_for_testing
        mock_requests.return_value.raise_for_status.return_value = None

        create_test_data(db_session_for_testing)

        # Execute
        process(mock_objects_with_notifications, mock_objects_without_notifications, sample_dataset_event)

        # Verify
        assert mock_requests.called
        # Check that it was called for dataset notification
        call_args = mock_requests.call_args
        payload_data = call_args[1]['data']  # keyword argument 'data'
        payload_dict = json.loads(payload_data)
        assert payload_dict['name'] == 'dataset-notification'
        assert payload_dict['to']['type'] == 'Subscriber'
        assert payload_dict['to']['subscriberId'] == 'user-dataset-123'

    @patch('listener_processing.main.db_session')
    @patch('requests.request')
    def test_process_collection_event_with_subscribers(
        self,
        mock_requests,
        mock_db_session,
        db_session_for_testing,
        sample_collection_event,
        mock_objects_with_notifications,
        mock_objects_without_notifications
    ):
        """Test processing collection event with subscribers"""
        # Setup
        mock_db_session.return_value = db_session_for_testing
        mock_requests.return_value.raise_for_status.return_value = None
        create_test_data(db_session_for_testing)

        # Execute
        process(mock_objects_with_notifications, mock_objects_without_notifications, sample_collection_event)

        # Verify
        assert mock_requests.called
        # Check that it was called for collection notification
        call_args = mock_requests.call_args
        payload_data = call_args[1]['data']
        payload_dict = json.loads(payload_data)
        assert payload_dict['name'] == 'dataset-collection-notification'
        assert payload_dict['to']['type'] == 'Subscriber'
        assert payload_dict['to']['subscriberId'] == 'user-org-456'

    @patch('listener_processing.main.db_session')
    @patch('listener_processing.novu.send_notifications_to_users')
    def test_process_dataset_event_no_subscribers(
        self,
        mock_send_notifications,
        mock_db_session,
        db_session_for_testing,
        sample_dataset_event,
        mock_objects_with_notifications,
        mock_objects_without_notifications
    ):
        """Test processing dataset event with no subscribers"""
        # Setup - don't create any test data, so no subscribers exist
        mock_db_session.return_value = db_session_for_testing

        # Execute
        process(mock_objects_with_notifications, mock_objects_without_notifications, sample_dataset_event)

        # Verify - no notifications should be sent
        mock_send_notifications.assert_not_called()

    @patch('listener_processing.main.db_session')
    @patch('listener_processing.novu.send_notifications_to_users')
    def test_process_skip_quickcharts_resource(
        self,
        mock_send_notifications,
        mock_db_session,
        db_session_for_testing,
        sample_dataset_event,
        mock_objects_with_notifications,
        mock_objects_without_notifications
    ):
        """Test that QuickCharts resources are skipped"""
        # Setup
        mock_db_session.return_value = db_session_for_testing
        create_test_data(db_session_for_testing)

        # Modify event to have QuickCharts in resource name
        sample_dataset_event['resource_name'] = 'Testing QuickCharts file.csv'

        # Execute
        process(mock_objects_with_notifications, mock_objects_without_notifications, sample_dataset_event)

        # Verify - no notifications should be sent due to skip logic
        mock_send_notifications.assert_not_called()

    @patch('requests.request')
    def test_handle_dataset_event_directly(
        self,
        mock_requests,
        db_session_for_testing,
        sample_dataset_event
    ):
        """Test _handle_dataset_event function directly"""
        # Setup
        mock_requests.return_value.raise_for_status.return_value = None
        create_test_data(db_session_for_testing)

        # Execute
        _handle_dataset_event(db_session_for_testing, sample_dataset_event)

        # Verify
        assert mock_requests.called
        call_args = mock_requests.call_args
        payload_data = call_args[1]['data']
        payload_dict = json.loads(payload_data)
        assert payload_dict['name'] == 'dataset-notification'
        assert payload_dict['to']['subscriberId'] == 'user-dataset-123'
        assert payload_dict['payload']['dataset_id'] == 'test-dataset-123'

    @patch('requests.request')
    def test_handle_collection_event_directly(
        self,
        mock_requests,
        db_session_for_testing,
        sample_collection_event
    ):
        """Test _handle_collection_event function directly"""
        # Setup
        mock_requests.return_value.raise_for_status.return_value = None
        create_test_data(db_session_for_testing)

        # Execute
        _handle_collection_event(db_session_for_testing, sample_collection_event)

        # Verify
        assert mock_requests.called
        call_args = mock_requests.call_args
        payload_data = call_args[1]['data']
        payload_dict = json.loads(payload_data)
        assert payload_dict['name'] == 'dataset-collection-notification'
        assert payload_dict['to']['subscriberId'] == 'user-org-456'
        assert payload_dict['payload']['object_type'] == 'organization'
        assert payload_dict['payload']['added_datasets'] == ['dataset-1', 'dataset-2', 'dataset-3']

    @patch('requests.request')
    def test_handle_dataset_event_missing_dataset_id(
        self,
        mock_requests,
        db_session_for_testing
    ):
        """Test _handle_dataset_event with missing dataset_id"""
        # Setup - event without dataset_id
        event = {
            'event_type': EVENT_TYPE_RESOURCE_CREATED,
            'resource_name': 'test-file.csv'
            # Missing dataset_id
        }

        # Execute
        _handle_dataset_event(db_session_for_testing, event)

        # Verify - no HTTP requests should be made
        mock_requests.assert_not_called()

    @patch('requests.request')
    def test_handle_collection_event_missing_object_info(
        self,
        mock_requests,
        db_session_for_testing
    ):
        """Test _handle_collection_event with missing object info"""
        # Setup - event without object_id or object_type
        event = {
            'event_type': EVENT_TYPE_ORG_DATASET_ADDED,
            'added_datasets': ['dataset-1', 'dataset-2']
            # Missing object_id and object_type
        }

        # Execute
        _handle_collection_event(db_session_for_testing, event)

        # Verify - no HTTP requests should be made
        mock_requests.assert_not_called()

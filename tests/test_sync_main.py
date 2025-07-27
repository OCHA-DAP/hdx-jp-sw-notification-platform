import pytest
import uuid
from unittest.mock import patch

from common.model import NotifyObject, Dataset, Subscription
from common.utils import generate_object_hash_id
from sync_processing.main import process_dataset_to_user
from config.config import get_config



@pytest.fixture
def sample_ckan_data():
    """Sample data that would come from CKAN API"""
    return {
        'inactive_subscriptions': [
            {'id': str(uuid.uuid4())},
            {'id': str(uuid.uuid4())}
        ],
        'grouped_subscriptions': [
            {
                'object': 'test-org-1',
                'object_type': 'organization',
                'user_list': [
                    {
                        'subscription_id': str(uuid.uuid4()),
                        'user_id': 'user-1',
                        'event_type': 'new-dataset-added'
                    },
                    {
                        'subscription_id': str(uuid.uuid4()),
                        'user_id': 'user-2',
                        'event_type': 'new-dataset-added'
                    }
                ]
            },
            {
                'object': 'test-group-1',
                'object_type': 'group',
                'user_list': [
                    {
                        'subscription_id': str(uuid.uuid4()),
                        'user_id': 'user-3',
                        'event_type': 'dataset-created'
                    }
                ]
            }
        ],
        'datasets': {
            'test-org-1': [
                {'id': 'dataset-1'},
                {'id': 'dataset-2'},
                {'id': 'dataset-3'}
            ],
            'test-group-1': [
                {'id': 'dataset-4'},
                {'id': 'dataset-5'}
            ]
        }
    }


class TestSyncLogic:
    """Test class for sync logic in main.py"""

    @patch('sync_processing.main._push_to_event_bus')
    @patch('sync_processing.main.hdx_get_datasets_ids_by_object')
    @patch('sync_processing.main.hdx_notifications_grouped_subscription_list')
    @patch('sync_processing.main.hdx_notifications_subscription_list')
    def test_basic_sync(self, mock_subscription_list, mock_grouped_list,
                                   mock_datasets, mock_event_bus, db_session_for_testing, sample_ckan_data):
        """Test 1: Basic sync with new subscriptions and datasets"""
        # Setup mocks
        mock_subscription_list.return_value = []  # No inactive subscriptions
        mock_grouped_list.return_value = sample_ckan_data['grouped_subscriptions']

        def mock_get_datasets(params):
            object_id = params['object_id']
            return sample_ckan_data['datasets'].get(object_id, [])

        mock_datasets.side_effect = mock_get_datasets

        # Run the sync process
        process_dataset_to_user()

        # Verify objects were created
        objects = db_session_for_testing.query(NotifyObject).all()
        assert len(objects) == 2

        org_object = db_session_for_testing.query(NotifyObject).filter_by(
            type='organization', hdx_id='test-org-1'
        ).first()
        group_object = db_session_for_testing.query(NotifyObject).filter_by(
            type='group', hdx_id='test-group-1'
        ).first()

        assert org_object is not None
        assert group_object is not None

        # Verify datasets were created
        datasets = db_session_for_testing.query(Dataset).all()
        assert len(datasets) == 5  # 3 for org + 2 for group

        org_datasets = db_session_for_testing.query(Dataset).filter_by(
            notify_object_id=org_object.id
        ).all()
        assert len(org_datasets) == 3

        # Verify subscriptions were created
        subscriptions = db_session_for_testing.query(Subscription).all()
        assert len(subscriptions) == 3  # 2 for org + 1 for group

        # Verify event bus was called for dataset collection types
        assert mock_event_bus.call_count == 2  # Both org and group are in DATASET_COLLECTION_TYPES

    @patch('sync_processing.main._push_to_event_bus')
    @patch('sync_processing.main.hdx_get_datasets_ids_by_object')
    @patch('sync_processing.main.hdx_notifications_grouped_subscription_list')
    @patch('sync_processing.main.hdx_notifications_subscription_list')
    def test_cleanup_inactive_subscriptions(self, mock_subscription_list, mock_grouped_list,
                                          mock_datasets, mock_event_bus, db_session_for_testing, sample_ckan_data):
        """Test 2: Cleanup of inactive subscriptions"""
        # Create some existing subscriptions to be deleted
        existing_object = NotifyObject(type='organization', hdx_id='old-org')
        db_session_for_testing.add(existing_object)
        db_session_for_testing.flush()

        inactive_sub_id = uuid.uuid4()
        inactive_subscription = Subscription(
            subscription_id=inactive_sub_id,
            user_id='old-user',
            event_type='new-dataset-added',
            notify_object_id=existing_object.id
        )
        db_session_for_testing.add(inactive_subscription)
        db_session_for_testing.commit()

        # Setup mocks - return the inactive subscription for deletion
        mock_subscription_list.return_value = [{'id': str(inactive_sub_id)}]
        mock_grouped_list.return_value = []  # No active subscriptions

        # Run sync process
        process_dataset_to_user()

        # Verify inactive subscription was deleted
        remaining_subscriptions = db_session_for_testing.query(Subscription).all()
        assert len(remaining_subscriptions) == 0

        # Verify orphaned object was also deleted
        remaining_objects = db_session_for_testing.query(NotifyObject).all()
        assert len(remaining_objects) == 0

    @patch('sync_processing.main._push_to_event_bus')
    @patch('sync_processing.main.hdx_get_datasets_ids_by_object')
    @patch('sync_processing.main.hdx_notifications_grouped_subscription_list')
    @patch('sync_processing.main.hdx_notifications_subscription_list')
    def test_removal_outdated_datasets(
        self, mock_subscription_list, mock_grouped_list,
        mock_datasets, mock_event_bus, db_session_for_testing, sample_ckan_data
    ):
        # Create existing object with datasets AND a subscription so it's not orphaned
        existing_object = NotifyObject(type='organization', hdx_id='test-org-1')
        db_session_for_testing.add(existing_object)
        db_session_for_testing.flush()

        # Add a subscription so the object doesn't get deleted as orphaned
        existing_subscription = Subscription(
            subscription_id=uuid.uuid4(),
            user_id='existing-user',
            event_type='new-dataset-added',
            notify_object_id=existing_object.id
        )
        db_session_for_testing.add(existing_subscription)

        # Create some existing datasets (some will be outdated)
        outdated_dataset = Dataset(
            dataset_id='old-dataset',
            notify_object_id=existing_object.id
        )
        outdated_dataset.id = generate_object_hash_id('organization', 'test-org-1', 'old-dataset')
        db_session_for_testing.add(outdated_dataset)

        kept_dataset = Dataset(
            dataset_id='dataset-1',
            notify_object_id=existing_object.id
        )
        kept_dataset.id = generate_object_hash_id('organization', 'test-org-1', 'dataset-1')
        db_session_for_testing.add(kept_dataset)
        db_session_for_testing.commit()

        # Setup mocks - make sure the new subscription data includes our existing subscription
        updated_ckan_data = sample_ckan_data['grouped_subscriptions'].copy()
        # Update the first subscription to include our existing subscription
        updated_ckan_data[0]['user_list'].append({
            'subscription_id': str(existing_subscription.id),
            'user_id': 'existing-user',
            'event_type': 'new-dataset-added'
        })

        mock_subscription_list.return_value = []
        mock_grouped_list.return_value = updated_ckan_data

        def mock_get_datasets(params):
            object_id = params['object_id']
            return sample_ckan_data['datasets'].get(object_id, [])

        mock_datasets.side_effect = mock_get_datasets

        # Run sync process
        process_dataset_to_user()

        # Re-query the object to avoid detached session issues
        existing_object = db_session_for_testing.query(NotifyObject).filter_by(
            type='organization', hdx_id='test-org-1'
        ).first()

        # Verify outdated dataset was removed
        remaining_datasets = db_session_for_testing.query(Dataset).filter_by(
            notify_object_id=existing_object.id
        ).all()

        dataset_ids = [d.dataset_id for d in remaining_datasets]
        assert 'old-dataset' not in dataset_ids
        assert 'dataset-1' in dataset_ids
        assert 'dataset-2' in dataset_ids
        assert 'dataset-3' in dataset_ids

    @patch('sync_processing.main._push_to_event_bus')
    @patch('sync_processing.main.hdx_get_datasets_ids_by_object')
    @patch('sync_processing.main.hdx_notifications_grouped_subscription_list')
    @patch('sync_processing.main.hdx_notifications_subscription_list')
    def test_different_object_types_event_handling(self, mock_subscription_list, mock_grouped_list,
                                                  mock_datasets, mock_event_bus, db_session_for_testing):
        # Create test data with different object types
        test_subscriptions = [
            {
                'object': 'test-org',
                'object_type': 'organization',  # Should trigger event
                'user_list': [
                    {
                        'subscription_id': str(uuid.uuid4()),
                        'user_id': 'user-1',
                        'event_type': 'new-dataset-added'
                    }
                ]
            },
            {
                'object': 'test-crisis',
                'object_type': 'crisis',  # Should trigger event
                'user_list': [
                    {
                        'subscription_id': str(uuid.uuid4()),
                        'user_id': 'user-2',
                        'event_type': 'new-dataset-added'
                    }
                ]
            },
            {
                'object': 'test-dataset',
                'object_type': 'dataset',  # Should NOT trigger event (not in DATASET_COLLECTION_TYPES)
                'user_list': [
                    {
                        'subscription_id': str(uuid.uuid4()),
                        'user_id': 'user-3',
                        'event_type': 'new-dataset-added'
                    }
                ]
            }
        ]

        # Setup mocks
        mock_subscription_list.return_value = []
        mock_grouped_list.return_value = test_subscriptions
        mock_datasets.return_value = [{'id': 'test-dataset-1'}]

        # Run sync process
        process_dataset_to_user()

        # Verify all objects were created
        objects = db_session_for_testing.query(NotifyObject).all()
        assert len(objects) == 3

        # Verify subscriptions were created for all object types
        subscriptions = db_session_for_testing.query(Subscription).all()
        assert len(subscriptions) == 3

        # Verify event bus was called only for organization and crisis (not dataset)
        assert mock_event_bus.call_count == 2

        # Check the event bus calls
        event_calls = mock_event_bus.call_args_list
        called_object_types = [call[0][1] for call in event_calls]  # Second argument is object_type
        assert 'organization' in called_object_types
        assert 'crisis' in called_object_types

    def test_error_handling_and_rollback(self, db_session_for_testing):
        # Create some initial data with a subscription so it doesn't get deleted as orphaned
        test_object = NotifyObject(type='organization', hdx_id='test-org')
        db_session_for_testing.add(test_object)
        db_session_for_testing.flush()

        # Add a subscription so the object doesn't get deleted in the orphan cleanup
        test_subscription = Subscription(
            subscription_id=uuid.uuid4(),
            user_id='test-user',
            event_type='new-dataset-added',
            notify_object_id=test_object.id
        )
        db_session_for_testing.add(test_subscription)
        db_session_for_testing.commit()

        initial_object_count = db_session_for_testing.query(NotifyObject).count()
        initial_subscription_count = db_session_for_testing.query(Subscription).count()

        # Mock to raise an exception during processing (after the orphan cleanup step)
        with patch('sync_processing.main.hdx_notifications_subscription_list') as mock_sub_list, \
             patch('sync_processing.main.hdx_notifications_grouped_subscription_list') as mock_grouped_list:

            mock_sub_list.return_value = []  # No inactive subscriptions to delete
            mock_grouped_list.side_effect = Exception('CKAN API Error')  # This will cause the exception

            # Run sync process and expect it to raise an exception
            with pytest.raises(Exception, match='CKAN API Error'):
                process_dataset_to_user()

        # Verify that no partial changes were committed (rollback worked)
        # The object and subscription should still exist since the error happened after orphan cleanup
        final_object_count = db_session_for_testing.query(NotifyObject).count()
        final_subscription_count = db_session_for_testing.query(Subscription).count()

        assert final_object_count == initial_object_count
        assert final_subscription_count == initial_subscription_count

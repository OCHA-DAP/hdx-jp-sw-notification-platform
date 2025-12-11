import pytest
from unittest.mock import patch
from requests.exceptions import HTTPError

from sync_processing.get import hdx_get_datasets_metadata, hdx_get_object_metadata
from sync_processing.main import _push_to_event_bus


class TestDatasetMetadataEnrichment:
    """Test suite for dataset metadata enrichment functionality"""

    @patch('sync_processing.get.hdx_action')
    def test_hdx_get_datasets_metadata_success(self, mock_hdx_action):
        """Test successful dataset metadata retrieval"""
        # Setup
        dataset_ids = ['dataset-1', 'dataset-2']
        mock_response = {
            'results': [
                {
                    'id': 'dataset-1',
                    'name': 'dataset-1-name',
                    'title': 'Dataset 1 Title',
                    'organization_title': 'Org 1 Title'
                },
                {
                    'id': 'dataset-2',
                    'name': 'dataset-2-name',
                    'title': 'Dataset 2 Title',
                    'organization_title': 'Org 2 Title'
                }
            ]
        }
        mock_hdx_action.return_value = mock_response

        # Execute
        result = hdx_get_datasets_metadata(dataset_ids)

        # Verify
        assert len(result) == 2
        assert result[0]['id'] == 'dataset-1'
        assert result[0]['name'] == 'dataset-1-name'
        assert result[0]['title'] == 'Dataset 1 Title'
        assert result[0]['organization_title'] == 'Org 1 Title'
        assert result[1]['id'] == 'dataset-2'
        assert result[1]['name'] == 'dataset-2-name'
        assert result[1]['title'] == 'Dataset 2 Title'
        assert result[1]['organization_title'] == 'Org 2 Title'

        # Verify the API call was made correctly
        mock_hdx_action.assert_called_once()
        call_args = mock_hdx_action.call_args
        url = call_args[0][0]
        params = call_args[0][1]

        assert '/api/3/action/package_search' in url
        assert params['q'] == 'id:dataset-1 OR id:dataset-2'
        assert params['rows'] == 2
        # assert params['fl'] == 'id,name,title'

    @patch('sync_processing.get.hdx_action')
    def test_hdx_get_datasets_metadata_api_error(self, mock_hdx_action):
        """Test dataset metadata retrieval when API fails"""
        # Setup
        mock_hdx_action.side_effect = HTTPError('API Error')
        dataset_ids = ['dataset-1']

        # Execute & Verify
        with pytest.raises(HTTPError):
            hdx_get_datasets_metadata(dataset_ids)


class TestObjectMetadataEnrichment:
    """Test suite for object metadata enrichment functionality"""

    @patch('sync_processing.get.hdx_action')
    def test_hdx_get_object_metadata_organization(self, mock_hdx_action):
        """Test successful organization metadata retrieval"""
        # Setup
        mock_response = {
            'id': 'test-org',
            'name': 'test-organization',
            'title': 'Test Organization Title'
        }
        mock_hdx_action.return_value = mock_response

        # Execute
        result = hdx_get_object_metadata('test-org', 'organization')

        # Verify
        assert result['id'] == 'test-org'
        assert result['name'] == 'test-organization'
        assert result['title'] == 'Test Organization Title'

        # Verify the API call was made correctly
        mock_hdx_action.assert_called_once()
        call_args = mock_hdx_action.call_args
        url = call_args[0][0]
        params = call_args[0][1]

        assert '/api/3/action/organization_show' in url
        assert params['id'] == 'test-org'

    @patch('sync_processing.get.hdx_action')
    def test_hdx_get_object_metadata_group(self, mock_hdx_action):
        """Test successful group metadata retrieval"""
        # Setup
        mock_response = {
            'id': 'test-group',
            'name': 'test-group-name',
            'title': 'Test Group Title'
        }
        mock_hdx_action.return_value = mock_response

        # Execute
        result = hdx_get_object_metadata('test-group', 'group')

        # Verify
        assert result['id'] == 'test-group'
        assert result['name'] == 'test-group-name'
        assert result['title'] == 'Test Group Title'

        # Verify the API call was made correctly
        mock_hdx_action.assert_called_once()
        call_args = mock_hdx_action.call_args
        url = call_args[0][0]

        assert '/api/3/action/group_show' in url

    @patch('sync_processing.get.hdx_action')
    def test_hdx_get_object_metadata_crisis(self, mock_hdx_action):
        """Test successful crisis metadata retrieval"""
        # Setup
        mock_response = {
            'id': 'test-crisis',
            'name': 'test-crisis-name',
            'title': 'Test Crisis Title'
        }
        mock_hdx_action.return_value = mock_response

        # Execute
        result = hdx_get_object_metadata('test-crisis', 'crisis')

        # Verify
        assert result['id'] == 'test-crisis'
        assert result['name'] == 'test-crisis-name'
        assert result['title'] == 'Test Crisis Title'

        # Verify the API call was made correctly
        mock_hdx_action.assert_called_once()
        call_args = mock_hdx_action.call_args
        url = call_args[0][0]

        assert '/api/3/action/page_show' in url

    def test_hdx_get_object_metadata_invalid_type(self):
        """Test object metadata retrieval with invalid object type"""
        # Execute & Verify
        with pytest.raises(ValueError, match='Unsupported object type: invalid'):
            hdx_get_object_metadata('test-id', 'invalid')

    @patch('sync_processing.get.hdx_action')
    def test_hdx_get_object_metadata_api_error(self, mock_hdx_action):
        """Test object metadata retrieval when API fails"""
        # Setup
        mock_hdx_action.side_effect = HTTPError('API Error')

        # Execute & Verify
        with pytest.raises(HTTPError):
            hdx_get_object_metadata('test-org', 'organization')


class TestEventBusEnrichment:
    """Test suite for event bus enrichment functionality"""

    @patch('sync_processing.main.event_bus')
    @patch('sync_processing.main.hdx_get_object_metadata')
    @patch('sync_processing.main.hdx_get_datasets_metadata')
    def test_push_to_event_bus_success(self, mock_datasets_metadata, mock_object_metadata, mock_event_bus):
        """Test successful event enrichment and push to event bus"""
        # Setup
        object_id = 'test-org'
        object_type = 'organization'
        datasets_to_be_inserted = [
            {'tid_hash': 'hash1', 'id': 'dataset-1'},
            {'tid_hash': 'hash2', 'id': 'dataset-2'}
        ]

        mock_object_metadata.return_value = {
            'id': 'test-org',
            'name': 'test-org-name',
            'title': 'Test Organization Title'
        }

        mock_datasets_metadata.return_value = [
            {
                'id': 'dataset-1',
                'name': 'dataset-1-name',
                'title': 'Dataset 1 Title',
                'organization': {'title': 'Org 1 Title'}
            },
            {
                'id': 'dataset-2',
                'name': 'dataset-2-name',
                'title': 'Dataset 2 Title',
                'organization': {'title': 'Org 2 Title'}
            }
        ]

        # Execute
        _push_to_event_bus(object_id, object_type, datasets_to_be_inserted)

        # Verify API calls
        mock_object_metadata.assert_called_once_with('test-org', 'organization')
        mock_datasets_metadata.assert_called_once_with(['dataset-1', 'dataset-2'])

        # Verify event bus call
        mock_event_bus.push_hdx_event.assert_called_once()
        event = mock_event_bus.push_hdx_event.call_args[0][0]

        # Verify event structure
        assert event['event_type'] == 'organization-dataset-added'
        assert event['object_type'] == 'organization'
        assert event['object_id'] == 'test-org'
        assert event['object_name'] == 'test-org-name'
        assert event['object_title'] == 'Test Organization Title'

        # Verify enriched dataset list
        assert len(event['added_datasets']) == 2

        dataset1 = event['added_datasets'][0]
        assert dataset1['tid_hash'] == 'hash1'
        assert dataset1['id'] == 'dataset-1'
        assert dataset1['name'] == 'dataset-1-name'
        assert dataset1['title'] == 'Dataset 1 Title'
        assert dataset1['organization_title'] == 'Org 1 Title'

        dataset2 = event['added_datasets'][1]
        assert dataset2['tid_hash'] == 'hash2'
        assert dataset2['id'] == 'dataset-2'
        assert dataset2['name'] == 'dataset-2-name'
        assert dataset2['title'] == 'Dataset 2 Title'
        assert dataset2['organization_title'] == 'Org 2 Title'

    @patch('sync_processing.main.event_bus')
    @patch('sync_processing.main.hdx_get_object_metadata')
    @patch('sync_processing.main.hdx_get_datasets_metadata')
    def test_push_to_event_bus_missing_dataset_metadata(
        self, mock_datasets_metadata, mock_object_metadata, mock_event_bus
    ):
        """Test event enrichment when some dataset metadata is missing"""
        # Setup
        object_id = 'test-org'
        object_type = 'organization'
        datasets_to_be_inserted = [
            {'tid_hash': 'hash1', 'id': 'dataset-1'},
            {'tid_hash': 'hash2', 'id': 'dataset-2'}
        ]

        mock_object_metadata.return_value = {
            'id': 'test-org',
            'name': 'test-org-name',
            'title': 'Test Organization Title'
        }

        # Only return metadata for one dataset
        mock_datasets_metadata.return_value = [
            {
                'id': 'dataset-1',
                'name': 'dataset-1-name',
                'title': 'Dataset 1 Title',
                'organization': {'title': 'Org 1 Title'}
            }
        ]

        # Execute
        _push_to_event_bus(object_id, object_type, datasets_to_be_inserted)

        # Verify event bus call
        mock_event_bus.push_hdx_event.assert_called_once()
        event = mock_event_bus.push_hdx_event.call_args[0][0]

        # Verify enriched dataset list
        assert len(event['added_datasets']) == 2

        # First dataset should have metadata
        dataset1 = event['added_datasets'][0]
        assert dataset1['name'] == 'dataset-1-name'
        assert dataset1['title'] == 'Dataset 1 Title'
        assert dataset1['organization_title'] == 'Org 1 Title'

        # Second dataset should have empty metadata
        dataset2 = event['added_datasets'][1]
        assert dataset2['name'] == ''
        assert dataset2['title'] == ''
        assert dataset2['organization_title'] == ''


    @patch('sync_processing.main.event_bus')
    @patch('sync_processing.main.hdx_get_object_metadata')
    @patch('sync_processing.main.hdx_get_datasets_metadata')
    def test_push_to_event_bus_dataset_metadata_error(
        self, mock_datasets_metadata, mock_object_metadata, mock_event_bus
    ):
        """Test event enrichment when dataset metadata retrieval fails"""
        # Setup
        mock_object_metadata.return_value = {'id': 'test-org', 'name': 'test-org-name', 'title': 'Test Org Title'}
        mock_datasets_metadata.side_effect = HTTPError('Dataset API Error')

        datasets_to_be_inserted = [{'tid_hash': 'hash1', 'id': 'dataset-1'}]

        # Execute & Verify
        with pytest.raises(HTTPError):
            _push_to_event_bus('test-org', 'organization', datasets_to_be_inserted)

        # Verify event bus was not called
        mock_event_bus.push_hdx_event.assert_not_called()

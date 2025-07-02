import logging
import mock
from processing.helpers import get_change_summary
from processing.objects import get_object_id_list
from processing.main import process as process

logger = logging.getLogger(__name__)


def _generate_resource_created_test_event():
    return {
        'event_type': 'resource-created',
        'event_time': '2024-10-02T11:22:15.973707',
        'event_source': 'ckan',
        'initiator_user_name': 'test-user',
        'dataset_name': 'test-dataset',
        'dataset_title': 'Test dataset',
        'dataset_id': 'test-dataset-id',
        'changed_fields': [
            {
                'field': 'microdata',
                'new_value': False,
                'new_display_value': 'does not contain microdata',
                'old_value': None,
                'old_display_value': 'does not contain microdata'
            },
            {
                'field': 'resource_type',
                'new_value': 'file.upload',
                'new_display_value': 'file.upload',
                'old_value': None,
                'old_display_value': None
            },
            {
                'field': 'name',
                'new_value': 'test.csv',
                'new_display_value': 'test.csv',
                'old_value': None,
                'old_display_value': None
            },
            {
                'field': 'format',
                'new_value': 'csv',
                'new_display_value': 'csv',
                'old_value': None,
                'old_display_value': None
            },
            {
                'field': 'url',
                'new_value': 'https://data.humdata.local/dataset/f679245a-5740-4ba6-a395-ec4e1ac20325/resource/b017f603-fb5e-4169-a7c5-88dbf202d368/download/test.csv',
                'new_display_value': 'https://data.humdata.local/dataset/f679245a-5740-4ba6-a395-ec4e1ac20325/resource/b017f603-fb5e-4169-a7c5-88dbf202d368/download/test.csv',
                'old_value': None,
                'old_display_value': None
            }
        ],
        'org_id': 'test-org-id',
        'org_name': 'test-org',
        'org_title': 'Test Org',
        'resource_name': 'test.csv',
        'resource_id': 'b017f603-fb5e-4169-a7c5-88dbf202d368'
    }



def test_get_change_summary():
    resource_create_event = _generate_resource_created_test_event()
    summary = get_change_summary(event=resource_create_event)
    assert resource_create_event.get('resource_name') in summary
    assert 'was created' in summary


def test_get_object_id_list():
    object_id_list = get_object_id_list()
    assert len(object_id_list) > 0

@mock.patch('processing.main.push_notification_to_novu')
def test_skip_values_not_skipping(push_notification_mock):
    event_dict = _generate_resource_created_test_event()
    process({'test-dataset-id'},event_dict)
    assert push_notification_mock.call_count == 1

@mock.patch('processing.main.push_notification_to_novu')
def test_skip_values_skipping(push_notification_mock):
    event_dict = _generate_resource_created_test_event()
    event_dict['resource_name'] = 'Testing QuickCharts file .csv'
    process({'test-dataset-id'}, event_dict)
    assert push_notification_mock.call_count == 0

import logging
import datetime
from typing import Dict, Set, List

from listener_processing.helpers import get_change_summary, get_email_event_type
from listener_processing.novu import push_notification_to_novu
from config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

def is_cached_expired(start_time: datetime, cache_time: datetime):
    cache_expiration_in_hours = int(config.HDX_OBJECTS_CSV_EXPIRATION_HOURS)
    if start_time - cache_time > datetime.timedelta(hours=cache_expiration_in_hours):
        return True
    else:
        return False

# List of resource names to skip
SKIP_RESOURCE_NAMES_LIST = ['QuickCharts', 'qc_data.csv', 'quickcharts', 'Quickcharts']

def contains_any_skip_resource(input_string: str, skip_list: List[str]):
    """
    Checks if the input string contains any item from the skip list.

    Args:
        input_string (str): The string to check.
        skip_list (list): A list of substrings to look for.

    Returns:
        bool: True if any item from the skip list is found, False otherwise.
    """
    return any(skip_item in input_string for skip_item in skip_list)

def process(objects_with_notifications: Set[str], objects_without_notifications: Set[str], event: Dict):
    if objects_with_notifications or objects_without_notifications:
        object_identifier = f"{event.get('object_type')}_{event.get('dataset_id')}"
        notifications_enabled = False
        if config.HDX_ENABLED_OBJECTS_CSV:
            notifications_enabled = object_identifier in objects_with_notifications
        elif config.HDX_DISABLED_OBJECTS_CSV:
            notifications_enabled = object_identifier not in objects_without_notifications

        # comment this line if you need to test local (without matching the object type+id to the list
        if event and 'dataset_id' in event and notifications_enabled:

            if not contains_any_skip_resource(event.get('resource_name', ''), SKIP_RESOURCE_NAMES_LIST):
                change_summary = get_change_summary(event)
                email_event_type = get_email_event_type(event)
                _dataset_id = event.get('dataset_id').replace('-', '_')
                data_dict = {
                    'event': event,
                    'email_event_type': email_event_type,
                    'resource_name': event.get('resource_name', ''),
                    'change_summary': change_summary,
                    'unsubscribe_token_key': f'unsubscribe_token_{_dataset_id}',
                    'hdx_url': config.HDX_URL
                }
                push_notification_to_novu(data_dict)

    else:
        pass  # object id list empty, pushing notification for every object?
    logger.info(f'Object name is {event.get("object_name")}')


import logging
import datetime
from typing import Dict, Set, List

from listener_processing.helpers import COLLECTION_EVENT_TYPES, get_change_summary, get_email_event_type
from listener_processing.novu import send_notifications_to_users
from common.model import Subscription
from common.db_utils import db_session
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

def _handle_collection_event(session, event: Dict):
    """Handle collection events (organization-dataset-added, crisis-dataset-added, group-dataset-added)"""
    object_id = event.get('object_id')
    object_type = event.get('object_type')

    if not object_id or not object_type:
        logger.warning(f'Missing object_id or object_type in collection event: {event}')
        return

    # Get users subscribed to this object
    user_ids = Subscription.get_users_subscribed_to_object(session, object_type, object_id)

    if not user_ids:
        logger.info(f'No users subscribed to {object_type} {object_id}')
        return

    # Prepare notification data
    email_event_type = get_email_event_type(event)
    data_dict = {
        'event': event,
        'email_event_type': email_event_type,
        # number of datasets that were added to the collection
        'change_summary': f'{len(event.get("added_datasets", []))} datasets added',
        'hdx_url': config.HDX_URL,
        'object_type': object_type,
        'object_id': object_id,
        'added_datasets': event.get('added_datasets', [])
    }

    # Send notifications to all subscribed users
    send_notifications_to_users(user_ids, data_dict, is_collection_event=True)
    logger.info(f'Sent collection notifications to {len(user_ids)} users for {object_type} {object_id}')

def _handle_dataset_event(session, event: Dict):
    """Handle regular dataset events (resource-created, resource-deleted, etc.)"""
    dataset_id = event.get('dataset_id')

    if not dataset_id:
        logger.warning(f'Missing dataset_id in dataset event: {event}')
        return

    # Check if we should skip this resource
    resource_name = event.get('resource_name', '')
    if resource_name and contains_any_skip_resource(resource_name, SKIP_RESOURCE_NAMES_LIST):
        logger.info(f'Skipping notification for resource: {resource_name}')
        return

    # Get users subscribed to this dataset
    user_ids = Subscription.get_users_subscribed_to_object(session, 'dataset', dataset_id)

    if not user_ids:
        logger.info(f'No users subscribed to dataset {dataset_id}')
        return

    # Prepare notification data
    resource_name = event.get('resource_name', '')
    change_summary = get_change_summary(event)
    email_event_type = get_email_event_type(event)
    data_dict = {
        'event': event,
        'email_event_type': email_event_type,
        'resource_name': resource_name,
        'change_summary': change_summary,
        'unsubscribe_token_key': f'unsubscribe_token_{dataset_id.replace("-", "_")}',
        'hdx_url': config.HDX_URL,
        'dataset_id': dataset_id
    }

    # Send notifications to all subscribed users
    send_notifications_to_users(user_ids, data_dict, is_collection_event=False)
    logger.info(f'Sent dataset notifications to {len(user_ids)} users for dataset {dataset_id}')

def process(objects_with_notifications: Set[str], objects_without_notifications: Set[str], event: Dict):
    """
    Process incoming events and send notifications to subscribed users.

    For dataset events (resource-created, resource-deleted, etc.):
    - Find users subscribed to the specific dataset
    - Send individual notifications using 'dataset-notification' workflow

    For collection events (organization-dataset-added, etc.):
    - Find users subscribed to the object (org/group/crisis)
    - Send individual notifications using 'dataset-collection-notification' workflow
    """
    if not (objects_with_notifications or objects_without_notifications):
        logger.info('No objects configured for notifications')
        return

    event_type = event.get('event_type')
    is_collection_event = event_type in COLLECTION_EVENT_TYPES

    # Check if notifications are enabled for this object
    notifications_enabled = _are_notifications_enabled(
        event, is_collection_event, objects_with_notifications, objects_without_notifications
    )

    if not notifications_enabled:
        logger.info(f'Notifications not enabled for object in event: {event.get("event_type")}')
        return

    if not event:
        logger.warning('Event is empty')
        return

    session = db_session()

    try:
        # Check if this is a collection event

        if is_collection_event:
            _handle_collection_event(session, event)
        else:
            _handle_dataset_event(session, event)

    except Exception as e:
        logger.error(f'Error processing event {event_type}: {e}')
        raise
    finally:
        session.close()

    logger.info(f'Processed event for object: {event.get("object_name", "unknown")}')


def _are_notifications_enabled(
    event: Dict,
    is_collection_event: bool,
    objects_with_notifications: Set[str],
    objects_without_notifications: Set[str],
) -> bool:

    if not is_collection_event:
        object_identifier = f"dataset_{event.get('dataset_id')}"
    elif event.get('object_id'):
        object_identifier = f"{event.get('object_type')}_{event.get('object_id')}"

    if object_identifier:
        if config.HDX_ENABLED_OBJECTS_CSV:
            return object_identifier in objects_with_notifications
        elif config.HDX_DISABLED_OBJECTS_CSV:
            return object_identifier not in objects_without_notifications

    return False

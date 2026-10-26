import functools
import logging
import requests
import json
from typing import Dict, List

from config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

# (connect, read) timeouts in seconds for every Novu request. Without them requests waits forever on a
# connection that stops responding (DATASET_NOTIFICATIONS-027).
NOVU_REQUEST_TIMEOUT = (10, 60)

DATASET_NOTIFICATION_WORKFLOW_ID = 'dataset-notification-v2'
# one notification per subscriber per dataset update run (DATASET_NOTIFICATIONS-016)
AGGREGATED_DATASET_NOTIFICATION_WORKFLOW_ID = 'dataset-notification-v3'


def push_notification_to_novu(data_dict: Dict):
    """Legacy function - kept for backward compatibility"""
    event = data_dict.get('event')
    dataset_id = event.get('dataset_id')
    url = config.NOVU_API_URL
    try:
        payload = json.dumps({
            'name': 'dataset-notification-v2',
            'to': {
                'type': 'Topic',
                'topicKey': f'dataset-{dataset_id}'
            },
            'payload': data_dict,
        })
    except Exception as ex:
        logger.error(ex)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'ApiKey {config.NOVU_API_KEY}'
    }

    response = requests.request('POST', url, headers=headers, data=payload, timeout=NOVU_REQUEST_TIMEOUT)

    print(response.text)
    logger.info('event pushed to NOVU')


def push_dataset_notification_to_user(user_id: str, data_dict: Dict,
                                      workflow_id: str = DATASET_NOTIFICATION_WORKFLOW_ID):
    """Send dataset notification directly to a specific user"""
    url = config.NOVU_API_URL
    try:
        payload = json.dumps({
            'name': workflow_id,
            'to': {
                'type': 'Subscriber',
                'subscriberId': user_id
            },
            'payload': data_dict,
        })
    except Exception as ex:
        logger.error(f'Error creating payload for user {user_id}: {ex}')
        return

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'ApiKey {config.NOVU_API_KEY}'
    }

    try:
        response = requests.request('POST', url, headers=headers, data=payload, timeout=NOVU_REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info(f'Dataset notification sent to user {user_id}')
    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to send dataset notification to user {user_id}: {e}')


def push_collection_notification_to_user(user_id: str, data_dict: Dict):
    """Send collection notification directly to a specific user"""
    url = config.NOVU_API_URL
    try:
        payload = json.dumps({
            'name': 'dataset-collection-notification',
            'to': {
                'type': 'Subscriber',
                'subscriberId': user_id
            },
            'payload': data_dict,
        })
    except Exception as ex:
        logger.error(f'Error creating collection payload for user {user_id}: {ex}')
        return

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'ApiKey {config.NOVU_API_KEY}'
    }

    try:
        response = requests.request('POST', url, headers=headers, data=payload, timeout=NOVU_REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info(f'Collection notification sent to user {user_id}')
    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to send collection notification to user {user_id}: {e}')


def send_notifications_to_users(user_ids: List[str], data_dict: Dict, is_collection_event: bool = False,
                                dataset_workflow_id: str = DATASET_NOTIFICATION_WORKFLOW_ID):
    """Send notifications to a list of users"""
    if not user_ids:
        logger.info('No users to notify')
        return

    if is_collection_event:
        notification_func = push_collection_notification_to_user
    else:
        notification_func = functools.partial(push_dataset_notification_to_user, workflow_id=dataset_workflow_id)

    for user_id in user_ids:
        notification_func(user_id, data_dict)

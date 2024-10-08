import logging
import requests
import json
from typing import Dict

from config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()


def push_notification_to_novu(data_dict: Dict):
    event = data_dict.get('event')
    dataset_id = event.get('dataset_id')
    url = config.NOVU_API_URL
    try:
        payload = json.dumps({
            'name': 'dataset-notification',
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

    response = requests.request('POST', url, headers=headers, data=payload)

    print(response.text)
    logger.info('event pushed to NOVU')

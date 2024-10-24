import logging
from typing import Dict, Set

from processing.helpers import get_change_summary
from processing.novu import push_notification_to_novu
from config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

def process(dataset_id_list: Set[str], event: Dict):
    if dataset_id_list:
        # comment this line if you need to test local (without matching the dataset id to the list
        if event and 'dataset_id' in event and event.get('dataset_id') in dataset_id_list:
            change_summary = get_change_summary(event)
            _dataset_id = event.get('dataset_id').replace('-', '_')
            data_dict = {
                'event': event,
                'change_summary': change_summary,
                'unsubscribe_token_key': f'unsubscribe_token_{_dataset_id}',
                'hdx_url': config.HDX_URL
            }
            push_notification_to_novu(data_dict)

    else:
        pass  # dataset id list empty, pushing notification for every dataset?
    logger.info(f'Dataset name is {event.get("dataset_name")}')

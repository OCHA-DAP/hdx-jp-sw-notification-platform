import logging
import datetime
from typing import Dict, Set, List

from processing.helpers import get_change_summary
from processing.novu import push_notification_to_novu
from config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

def is_cached_expired(start_time: datetime, cache_time: datetime):
    cache_expiration_in_hours = int(config.HDX_DATASETS_CSV_EXPIRATION_HOURS)
    if start_time - cache_time > datetime.timedelta(hours=cache_expiration_in_hours):
        return True
    else:
        return False

# List of resource names to skip
SKIP_RESOURCE_NAMES_LIST = ['QuickCharts', 'qc_data.csv']

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

def process(dataset_id_list: Set[str], event: Dict):
    if dataset_id_list:
        # comment this line if you need to test local (without matching the dataset id to the list
        if event and 'dataset_id' in event and event.get('dataset_id') in dataset_id_list:

            if not contains_any_skip_resource(event.get('resource_name', ''), SKIP_RESOURCE_NAMES_LIST):
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

import csv
import logging
from typing import Set

import requests

from config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
OBJECT_ID_LIST = None


def hdx_retrieve_objects_without_notifications() -> Set[str]:
    url = config.HDX_DISABLED_OBJECTS_CSV
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        logger.error(f'An error occurred: {error_msg}')
        raise Exception(f'Couldn\'t fetch objects without notifications from Google Spreadsheets: {error_msg}')

    csv_data = response.text
    csv_reader = csv.reader(csv_data.splitlines())
    # skip the csv header
    next(csv_reader)
    objects = {f'{row[1]}_{row[0]}' for row in csv_reader}
    return objects


def get_object_id_list(is_expired=False):
    global OBJECT_ID_LIST
    if not OBJECT_ID_LIST or is_expired:
        try:
            OBJECT_ID_LIST = hdx_retrieve_objects_without_notifications()
        except Exception as e:
            logger.error(e)
    return OBJECT_ID_LIST

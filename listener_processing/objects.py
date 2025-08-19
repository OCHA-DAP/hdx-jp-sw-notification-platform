import csv
import logging
from typing import Set

import requests

from config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
OBJECTS_WITH_NOTIFICATIONS = None
OBJECTS_WITHOUT_NOTIFICATIONS = None


def hdx_retrieve_objects_from_spreadsheet(notifications_enabled: bool) -> Set[str]:
    if notifications_enabled:
        url = config.HDX_ENABLED_OBJECTS_CSV
    else:
        url = config.HDX_DISABLED_OBJECTS_CSV

    if url:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f'An error occurred: {error_msg}')
            raise Exception(
                f'Couldn\'t fetch objects {"with" if notifications_enabled else "without"} notifications from '
                'Google Spreadsheets: {error_msg}'
            )

        csv_data = response.text
        csv_reader = csv.reader(csv_data.splitlines())

        # Validate headers and map column names to indices
        headers = next(csv_reader, None)
        if headers is None or 'object_id' not in headers or 'object_type' not in headers:
            raise Exception("CSV file is missing required headers: 'object_id' and 'object_type'")
        id_index = headers.index('object_id')
        type_index = headers.index('object_type')

        objects = {f'{row[type_index]}_{row[id_index]}' for row in csv_reader}
        return objects
    else:
        return set()


def get_objects_with_notifications(is_expired=False):
    global OBJECTS_WITH_NOTIFICATIONS
    if not OBJECTS_WITH_NOTIFICATIONS or is_expired:
        try:
            OBJECTS_WITH_NOTIFICATIONS = hdx_retrieve_objects_from_spreadsheet(notifications_enabled=True)
        except Exception as e:
            logger.error(e)
    return OBJECTS_WITH_NOTIFICATIONS


def get_objects_without_notifications(is_expired=False):
    global OBJECTS_WITHOUT_NOTIFICATIONS
    if not OBJECTS_WITHOUT_NOTIFICATIONS or is_expired:
        try:
            OBJECTS_WITHOUT_NOTIFICATIONS = hdx_retrieve_objects_from_spreadsheet(notifications_enabled=False)
        except Exception as e:
            logger.error(e)
    return OBJECTS_WITHOUT_NOTIFICATIONS

import csv
import logging
from typing import Set

import requests

from config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
DATASET_ID_LIST = None


def hdx_retrieve_datasets_with_notifications() -> Set[str]:
    url = config.GOOGLE_SHEETS_DATASET_ID_LIST_URL
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        logger.error(f'An error occurred: {error_msg}')
        raise Exception(f'Couldn\'t fetch datasets with notifications from Google Spreadsheets: {error_msg}')

    csv_data = response.text
    csv_reader = csv.reader(csv_data.splitlines())
    # skip the csv header
    next(csv_reader)
    datasets = {row[0] for row in csv_reader}
    return datasets


def get_dataset_id_list():
    global DATASET_ID_LIST
    if not DATASET_ID_LIST:
        try:
            DATASET_ID_LIST = hdx_retrieve_datasets_with_notifications()
        except Exception as e:
            logger.error(e)
    return DATASET_ID_LIST

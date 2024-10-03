import logging
from typing import Dict, Set

from helpers import EVENT_TYPE_RESOURCE_DELETED, EVENT_TYPE_RESOURCE_CREATED, EVENT_TYPE_RESOURCE_DATA_CHANGED, \
    EVENT_TYPE_SPREADSHEET_SHEET_CHANGED, EVENT_TYPE_SPREADSHEET_SHEET_CREATED, EVENT_TYPE_SPREADSHEET_SHEET_DELETED
from processing.novu import push_notification_to_novu

logger = logging.getLogger(__name__)


def _get_change_summary(event):
    ev_type = event.get('event_type')
    if ev_type == EVENT_TYPE_RESOURCE_CREATED:
        return f'{event.get('resource_name')} was created'
    if ev_type == EVENT_TYPE_RESOURCE_DELETED:
        return f'{event.get('resource_name')} was deleted'
    if ev_type == EVENT_TYPE_RESOURCE_DATA_CHANGED:
        return f'{event.get('resource_name')} was updated'
    if ev_type == EVENT_TYPE_SPREADSHEET_SHEET_CHANGED or ev_type == EVENT_TYPE_SPREADSHEET_SHEET_CREATED or ev_type == EVENT_TYPE_SPREADSHEET_SHEET_DELETED:
        return f'Resource structure was changed for {event.get('resource_name')}'


def process(dataset_id_list: Set[str], event: Dict):
    if dataset_id_list:
        if event and 'dataset_id' in event and event.get('dataset_id') in dataset_id_list:
            change_summary = _get_change_summary(event)
            data_dict = {
                'event': event,
                'change_summary': change_summary
            }
            push_notification_to_novu(data_dict)

    else:
        pass  # dataset id list empty, pushing notification for every dataset?
    logger.info(f'Dataset name is {event.get("dataset_name")}')

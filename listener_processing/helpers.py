import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)

EVENT_TYPE_RESOURCE_DELETED = 'resource-deleted'
EVENT_TYPE_RESOURCE_CREATED = 'resource-created'
EVENT_TYPE_RESOURCE_DATA_CHANGED = 'resource-data-changed'

# Fields for file structure_change: num_sheets, num_rows, num_cols, has_merged_cells, header, hxl_header
EVENT_TYPE_SPREADSHEET_SHEET_CREATED = 'spreadsheet-sheet-created'
EVENT_TYPE_SPREADSHEET_SHEET_DELETED = 'spreadsheet-sheet-deleted'
EVENT_TYPE_SPREADSHEET_SHEET_CHANGED = 'spreadsheet-sheet-changed'

EVENT_TYPE_ORG_DATASET_ADDED = 'organization-dataset-added'
EVENT_TYPE_CRISIS_DATASET_ADDED = 'crisis-dataset-added'
EVENT_TYPE_GROUP_DATASET_ADDED = 'group-dataset-added'

ALLOWED_EVENT_TYPES = {
    EVENT_TYPE_RESOURCE_DELETED,
    EVENT_TYPE_RESOURCE_CREATED,
    EVENT_TYPE_RESOURCE_DATA_CHANGED,

    EVENT_TYPE_SPREADSHEET_SHEET_CREATED,
    EVENT_TYPE_SPREADSHEET_SHEET_DELETED,
    EVENT_TYPE_SPREADSHEET_SHEET_CHANGED,

    EVENT_TYPE_ORG_DATASET_ADDED,
    EVENT_TYPE_CRISIS_DATASET_ADDED,
    EVENT_TYPE_GROUP_DATASET_ADDED,
}

def get_change_summary(event: Dict)->str:
    if event :
        ev_type = event.get('event_type')
        resource_name = event.get('resource_name', 'A resource')
        dataset_list = event.get('dataset_list', [])
        if ev_type == EVENT_TYPE_RESOURCE_CREATED:
            return f'The resource/file "{resource_name}" was created'
        if ev_type == EVENT_TYPE_RESOURCE_DELETED:
            return f'The resource/file "{resource_name}" was deleted'
        if ev_type == EVENT_TYPE_RESOURCE_DATA_CHANGED:
            return f'The resource/file "{resource_name}" was updated'
        if ev_type in {
            EVENT_TYPE_SPREADSHEET_SHEET_CHANGED,
            EVENT_TYPE_SPREADSHEET_SHEET_CREATED,
            EVENT_TYPE_SPREADSHEET_SHEET_DELETED,
        }:
            return f'The resource/file structure was changed for "{resource_name}"'
        if ev_type in {
            EVENT_TYPE_ORG_DATASET_ADDED,
            EVENT_TYPE_CRISIS_DATASET_ADDED,
            EVENT_TYPE_GROUP_DATASET_ADDED,
        }:
            return f'The following datasets were added: {", ".join(dataset_list)}'
    return None

def get_email_event_type(event: Dict) -> str:
    event_type = event.get('event_type')
    if event_type in {
        EVENT_TYPE_SPREADSHEET_SHEET_CREATED,
        EVENT_TYPE_SPREADSHEET_SHEET_DELETED,
        EVENT_TYPE_SPREADSHEET_SHEET_CHANGED,
    }:
        return 'spreadsheet-sheet-updated'
    return event_type

def do_nothing_for_ever():
    while True:
        logger.info('Worker is relaxing as it is not enabled')
        time.sleep(300)

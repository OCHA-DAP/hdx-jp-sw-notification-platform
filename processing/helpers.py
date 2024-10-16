import logging
import time

logger = logging.getLogger(__name__)

EVENT_TYPE_RESOURCE_DELETED = 'resource-deleted'
EVENT_TYPE_RESOURCE_CREATED = 'resource-created'
EVENT_TYPE_RESOURCE_DATA_CHANGED = 'resource-data-changed'

# Fields for file structure_change: num_sheets, num_rows, num_cols, has_merged_cells, header, hxl_header
EVENT_TYPE_SPREADSHEET_SHEET_CREATED = 'spreadsheet-sheet-created'
EVENT_TYPE_SPREADSHEET_SHEET_DELETED = 'spreadsheet-sheet-deleted'
EVENT_TYPE_SPREADSHEET_SHEET_CHANGED = 'spreadsheet-sheet-changed'

ALLOWED_EVENT_TYPES = {
    EVENT_TYPE_RESOURCE_DELETED,
    EVENT_TYPE_RESOURCE_CREATED,
    EVENT_TYPE_RESOURCE_DATA_CHANGED,

    EVENT_TYPE_SPREADSHEET_SHEET_CREATED,
    EVENT_TYPE_SPREADSHEET_SHEET_DELETED,
    EVENT_TYPE_SPREADSHEET_SHEET_CHANGED,
}

def get_change_summary(event):
    if event :
        ev_type = event.get('event_type')
        resource_name = event.get('resource_name','A resource')
        if ev_type == EVENT_TYPE_RESOURCE_CREATED:
            return f'The resource/file "{resource_name}" was created'
        if ev_type == EVENT_TYPE_RESOURCE_DELETED:
            return f'The resource/file "{resource_name}" was deleted'
        if ev_type == EVENT_TYPE_RESOURCE_DATA_CHANGED:
            return f'The resource/file "{resource_name}" was updated'
        if ev_type == EVENT_TYPE_SPREADSHEET_SHEET_CHANGED or ev_type == EVENT_TYPE_SPREADSHEET_SHEET_CREATED or ev_type == EVENT_TYPE_SPREADSHEET_SHEET_DELETED:
            return f'The resource/file structure was changed for "{resource_name}"'
    return None

def do_nothing_for_ever():
    while True:
        logger.info('Worker is relaxing as it is not enabled')
        time.sleep(300)

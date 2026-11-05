import datetime
import logging
import time
from typing import Dict, List

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

COLLECTION_EVENT_TYPES = {
    EVENT_TYPE_ORG_DATASET_ADDED,
    EVENT_TYPE_CRISIS_DATASET_ADDED,
    EVENT_TYPE_GROUP_DATASET_ADDED,
}

# Fields that, on their own, don't warrant a notification email for a
# spreadsheet-sheet-changed event. A pure row-count change from a routine data append
# (e.g. a daily cumulative-append dataset) is real, accurate information about the sheet -
# other listeners on this event stream may care about it - it's just not something
# subscribers need to be emailed about every single day (see HDX-11617).
NON_NOTIFYING_SPREADSHEET_FIELDS = {'nrows'}


def is_notification_worthy(event: Dict) -> bool:
    """
    Decide whether an event should result in a notification being sent.

    Every event type is notification-worthy except spreadsheet-sheet-changed events
    where *every* changed field is in NON_NOTIFYING_SPREADSHEET_FIELDS - e.g. a resource
    that only had rows appended, with its header/columns/hashtags unchanged. If at least
    one other field also changed (a genuine structural change), the event is still
    notification-worthy.
    """
    if event.get('event_type') != EVENT_TYPE_SPREADSHEET_SHEET_CHANGED:
        return True
    changed_field_names = {field.get('field') for field in (event.get('changed_fields') or [])}
    if not changed_field_names:
        # no changed_fields info to go on - don't suppress on unknown data
        return True
    return not changed_field_names.issubset(NON_NOTIFYING_SPREADSHEET_FIELDS)

def get_change_summary(event: Dict)->str:
    if event :
        ev_type = event.get('event_type')
        resource_name = event.get('resource_name', 'A resource')
        # dataset_list = event.get('dataset_list', [])
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
        # if ev_type in {
        #     EVENT_TYPE_ORG_DATASET_ADDED,
        #     EVENT_TYPE_CRISIS_DATASET_ADDED,
        #     EVENT_TYPE_GROUP_DATASET_ADDED,
        # }:
        #     return f'The following datasets were added: {", ".join(dataset_list)}'
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


def get_unsubscribe_token_key(dataset_id: str) -> str:
    return f'unsubscribe_token_{dataset_id.replace("-", "_")}'


def get_event_time(event: Dict) -> datetime.datetime:
    """The event's `event_time` as a datetime, for ordering. Missing or unparsable values sort first."""
    try:
        event_time = datetime.datetime.fromisoformat(event.get('event_time'))
    except (TypeError, ValueError):
        return datetime.datetime.min
    if event_time.tzinfo:
        # compare everything as naive UTC; HDX sends naive UTC timestamps
        event_time = event_time.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return event_time


def drop_superseded_by_delete(events: List[Dict]) -> List[Dict]:
    """
    Removes the events of a deleted resource that happened before its (latest) deletion, so that subscribers
    aren't told a file was added or updated when it no longer exists. If the resource was also created before
    that deletion, the deletion is removed as well: the file appeared and disappeared within the same group,
    so subscribers never knew about it (DATASET_NOTIFICATIONS-017).

    Events are matched by `resource_id` and ordered by `event_time`. Events without a `resource_id` are kept.
    """
    latest_delete_times = {}
    for event in events:
        resource_id = event.get('resource_id')
        if resource_id and event.get('event_type') == EVENT_TYPE_RESOURCE_DELETED:
            event_time = get_event_time(event)
            if resource_id not in latest_delete_times or event_time > latest_delete_times[resource_id]:
                latest_delete_times[resource_id] = event_time

    created_before_delete = {
        event['resource_id'] for event in events
        if event.get('resource_id') in latest_delete_times
        and event.get('event_type') == EVENT_TYPE_RESOURCE_CREATED
        and get_event_time(event) < latest_delete_times[event['resource_id']]
    }

    kept = []
    for event in events:
        resource_id = event.get('resource_id')
        if resource_id not in latest_delete_times:
            kept.append(event)
            continue
        event_time = get_event_time(event)
        delete_time = latest_delete_times[resource_id]
        if event_time < delete_time:
            continue
        if event_time == delete_time and event.get('event_type') == EVENT_TYPE_RESOURCE_DELETED \
                and resource_id in created_before_delete:
            continue
        kept.append(event)
    return kept


def build_changes(events: List[Dict]) -> List[Dict]:
    """
    The `changes` list of an aggregated notification: one entry per (email event type, resource), after applying
    deletions (DATASET_NOTIFICATIONS-017, -018). `events` should be in chronological order; the email template
    sorts the names itself.
    """
    changes = []
    seen = set()
    for event in drop_superseded_by_delete(events):
        email_event_type = get_email_event_type(event)
        key = (email_event_type, event.get('resource_id'))
        if key in seen:
            continue
        seen.add(key)
        changes.append({
            'email_event_type': email_event_type,
            'resource_name': event.get('resource_name'),
            'resource_id': event.get('resource_id'),
        })
    return changes

def do_nothing_for_ever():
    while True:
        logger.info('Worker is relaxing as it is not enabled')
        time.sleep(300)

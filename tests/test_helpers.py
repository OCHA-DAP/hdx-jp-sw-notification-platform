import datetime

from listener_processing.helpers import EVENT_TYPE_RESOURCE_CREATED, EVENT_TYPE_RESOURCE_DATA_CHANGED, \
    EVENT_TYPE_RESOURCE_DELETED, EVENT_TYPE_SPREADSHEET_SHEET_CHANGED, build_changes, drop_superseded_by_delete, \
    get_event_time, get_unsubscribe_token_key


def _event(event_type, resource_id, event_time, resource_name=None):
    return {
        'event_type': event_type,
        'event_time': event_time,
        'dataset_id': 'dataset-1',
        'resource_id': resource_id,
        'resource_name': resource_name or f'{resource_id}.csv',
    }


T1 = '2026-10-04T08:00:01.501234'
T2 = '2026-10-04T08:00:08.020511'
T3 = '2026-10-04T09:30:00.000001'


class TestGetEventTime:

    def test_parses_iso_timestamp(self):
        assert get_event_time({'event_time': T1}) == datetime.datetime(2026, 10, 4, 8, 0, 1, 501234)

    def test_missing_or_invalid_sorts_first(self):
        assert get_event_time({}) == datetime.datetime.min
        assert get_event_time({'event_time': 'not a date'}) == datetime.datetime.min

    def test_timezone_aware_is_compared_as_naive_utc(self):
        assert get_event_time({'event_time': '2026-10-04T10:00:00+02:00'}) == datetime.datetime(2026, 10, 4, 8, 0)


def test_get_unsubscribe_token_key():
    assert get_unsubscribe_token_key('a1b2-c3d4') == 'unsubscribe_token_a1b2_c3d4'


class TestDropSupersededByDelete:
    """DATASET_NOTIFICATIONS-017"""

    def test_no_deletes_keeps_everything(self):
        events = [
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T1),
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T2),
        ]
        assert drop_superseded_by_delete(events) == events

    def test_events_before_delete_are_dropped(self):
        changed = _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T1)
        sheet_changed = _event(EVENT_TYPE_SPREADSHEET_SHEET_CHANGED, 'r1', T1)
        deleted = _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T2)
        assert drop_superseded_by_delete([sheet_changed, changed, deleted]) == [deleted]

    def test_created_then_deleted_drops_everything(self):
        events = [
            _event(EVENT_TYPE_RESOURCE_CREATED, 'r1', T1),
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T2),
            _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T3),
        ]
        assert drop_superseded_by_delete(events) == []

    def test_only_the_deleted_resource_is_affected(self):
        other = _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r2', T1)
        deleted = _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T2)
        events = [_event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T1), other, deleted]
        assert drop_superseded_by_delete(events) == [other, deleted]

    def test_order_comes_from_event_time_not_list_position(self):
        # the 3 listeners insert in parallel, so the delete may come first in the list
        deleted = _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T2)
        assert drop_superseded_by_delete([deleted, _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T1)]) == [deleted]

    def test_events_after_the_latest_delete_are_kept(self):
        first_delete = _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T1)
        latest_delete = _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T2)
        later_change = _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T3)
        assert drop_superseded_by_delete([first_delete, latest_delete, later_change]) == [latest_delete, later_change]

    def test_delete_and_recreate_under_new_id_keeps_both(self):
        deleted = _event(EVENT_TYPE_RESOURCE_DELETED, 'r-old', T1, resource_name='points.geojson')
        created = _event(EVENT_TYPE_RESOURCE_CREATED, 'r-new', T1, resource_name='points.geojson')
        assert drop_superseded_by_delete([deleted, created]) == [deleted, created]

    def test_events_without_resource_id_are_kept(self):
        no_resource = _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, None, T1)
        assert drop_superseded_by_delete([no_resource, _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T2)])[0] == no_resource


class TestBuildChanges:
    """DATASET_NOTIFICATIONS-017, -018"""

    def test_one_entry_per_type_and_resource(self):
        events = [
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T1),
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T2),
            _event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r2', T1),
        ]
        assert build_changes(events) == [
            {'email_event_type': EVENT_TYPE_RESOURCE_DATA_CHANGED, 'resource_name': 'r1.csv', 'resource_id': 'r1'},
            {'email_event_type': EVENT_TYPE_RESOURCE_DATA_CHANGED, 'resource_name': 'r2.csv', 'resource_id': 'r2'},
        ]

    def test_two_resources_with_the_same_name_stay_separate(self):
        events = [
            _event(EVENT_TYPE_RESOURCE_CREATED, 'r1', T1, resource_name='data.csv'),
            _event(EVENT_TYPE_RESOURCE_CREATED, 'r2', T1, resource_name='data.csv'),
        ]
        assert [c['resource_id'] for c in build_changes(events)] == ['r1', 'r2']

    def test_uses_email_event_type(self):
        changes = build_changes([_event(EVENT_TYPE_SPREADSHEET_SHEET_CHANGED, 'r1', T1)])
        assert changes[0]['email_event_type'] == 'spreadsheet-sheet-updated'

    def test_applies_deletes(self):
        events = [_event(EVENT_TYPE_RESOURCE_DATA_CHANGED, 'r1', T1), _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T2)]
        assert build_changes(events) == [
            {'email_event_type': EVENT_TYPE_RESOURCE_DELETED, 'resource_name': 'r1.csv', 'resource_id': 'r1'},
        ]

    def test_created_and_deleted_in_the_same_group_is_empty(self):
        events = [_event(EVENT_TYPE_RESOURCE_CREATED, 'r1', T1), _event(EVENT_TYPE_RESOURCE_DELETED, 'r1', T2)]
        assert build_changes(events) == []

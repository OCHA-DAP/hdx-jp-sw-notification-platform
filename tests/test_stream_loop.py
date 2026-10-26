from unittest.mock import MagicMock, patch

from listener_processing.helpers import EVENT_TYPE_RESOURCE_CREATED
from listener_processing.stream_loop import FLUSH_INTERVAL_SECONDS, listen


def _event_bus(*events):
    event_bus = MagicMock()
    event_bus.read_hdx_event.side_effect = list(events)
    return event_bus


class TestListen:
    """DATASET_NOTIFICATIONS-013, -025"""

    @patch('listener_processing.stream_loop.time.monotonic', side_effect=[0, 1, 2])
    def test_processes_only_allowed_event_types(self, mock_monotonic):
        allowed = {'event_type': EVENT_TYPE_RESOURCE_CREATED}
        event_bus = _event_bus(allowed, {'event_type': 'dataset-deleted'}, None)
        processor = MagicMock(return_value=(True, 'Success'))

        listen(event_bus, processor, flush=MagicMock(), max_iterations=3)

        processor.assert_called_once_with(allowed)
        # hdx-redis-lib's default read wait (120 s) is kept (-025)
        event_bus.read_hdx_event.assert_called_with()

    def test_flush_interval_matches_the_default_read_wait(self):
        assert FLUSH_INTERVAL_SECONDS == 120

    @patch('listener_processing.stream_loop.time.monotonic', side_effect=[0, 50, 119.9, 120, 200, 241])
    def test_flushes_at_most_once_per_interval_even_without_events(self, mock_monotonic):
        event_bus = _event_bus(None, None, None, None, None, None)
        flush = MagicMock()

        listen(event_bus, MagicMock(), flush=flush, max_iterations=6)

        # flushes at t=0 (first read), t=120 and t=241
        assert flush.call_count == 3

    @patch('listener_processing.stream_loop.time.monotonic', side_effect=[0, 1])
    def test_stops_after_max_iterations(self, mock_monotonic):
        event_bus = _event_bus(None, None, None)

        listen(event_bus, MagicMock(), flush=MagicMock(), max_iterations=2)

        assert event_bus.read_hdx_event.call_count == 2

    @patch('listener_processing.stream_loop.time.monotonic', return_value=0)
    def test_error_ends_the_loop_and_is_logged(self, mock_monotonic, caplog):
        event_bus = _event_bus({'event_type': EVENT_TYPE_RESOURCE_CREATED}, None)
        processor = MagicMock(side_effect=Exception('boom'))

        listen(event_bus, processor, flush=MagicMock(), max_iterations=5)

        assert event_bus.read_hdx_event.call_count == 1
        assert 'boom' in caplog.text

    @patch('listener_processing.stream_loop.time.monotonic', return_value=0)
    def test_unsuccessful_processing_is_logged_and_listening_continues(self, mock_monotonic, caplog):
        event_bus = _event_bus({'event_type': EVENT_TYPE_RESOURCE_CREATED}, None)
        processor = MagicMock(return_value=(False, 'bad event'))

        listen(event_bus, processor, flush=MagicMock(), max_iterations=2)

        assert event_bus.read_hdx_event.call_count == 2
        assert 'Event processor decided to stop. Reason: bad event' in caplog.text

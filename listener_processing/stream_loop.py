import logging
import time
from typing import Callable, Dict, Tuple

from listener_processing.helpers import ALLOWED_EVENT_TYPES

logger = logging.getLogger(__name__)

# How often each listener checks for due datasets (DATASET_NOTIFICATIONS-013). 120 s is chosen to match
# hdx-redis-lib's default read wait (DEFAULT_READ_BLOCK_MS), which the loop keeps (-025): an idle read returns
# after 120 s, so an idle listener checks as often as a busy one. A shorter interval would only be honoured
# while events are flowing.
FLUSH_INTERVAL_SECONDS = 120


def listen(event_bus, event_processor: Callable[[Dict], Tuple[bool, str]], flush: Callable[[], None],
           max_iterations: int):
    """
    Reads HDX events from the stream and processes the allowed ones, like hdx-redis-lib's hdx_listen(), and also
    calls `flush` at most once every FLUSH_INTERVAL_SECONDS, including when no events arrive
    (DATASET_NOTIFICATIONS-013, -025). hdx_listen() only calls back when an event arrives, so it can't drive the
    flush.

    As with hdx_listen(), the loop ends after `max_iterations` reads, or on the first unhandled error, which is
    logged.
    """
    last_flush = None
    try:
        for _ in range(max_iterations):
            event = event_bus.read_hdx_event()
            if event and event.get('event_type') in ALLOWED_EVENT_TYPES:
                result, message = event_processor(event)
                if not result:
                    logger.error('Event processor decided to stop. Reason: {}'.format(message))
            else:
                logger.info('Event with value None arrived')

            now = time.monotonic()
            if last_flush is None or now - last_flush >= FLUSH_INTERVAL_SECONDS:
                flush()
                last_flush = now
        logger.info('Exiting listening function because max iteration was reached')
    except Exception as e:
        logger.error(str(e))

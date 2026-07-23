import logging.config

logging.config.fileConfig('logging.conf')

import datetime  # noqa
import json  # noqa
from hdx_redis_lib import connect_to_hdx_event_bus_with_env_vars  # noqa
from config.config import get_config  # noqa
from listener_processing.objects import get_objects_with_notifications, get_objects_without_notifications  # noqa
from listener_processing.helpers import ALLOWED_EVENT_TYPES  # noqa
from listener_processing.helpers import do_nothing_for_ever  # noqa
from listener_processing.main import process, is_cached_expired  # noqa



logger = logging.getLogger(__name__)


config = get_config()

objects_with_notifications = get_objects_with_notifications()
objects_without_notifications = get_objects_without_notifications()
cache_time = datetime.datetime.now()

if __name__ == '__main__':

    if not config.WORKER_ENABLED:
        do_nothing_for_ever()
    else:

        def event_processor(event):
            global objects_with_notifications
            global objects_without_notifications
            global cache_time

            logger.info('Received event: ' + json.dumps(event, ensure_ascii=False, indent=4))
            start_time = datetime.datetime.now()
            if is_cached_expired(start_time, cache_time):
                objects_with_notifications = get_objects_with_notifications(is_expired=True)
                objects_without_notifications = get_objects_without_notifications(is_expired=True)
                cache_time = datetime.datetime.now()
            process(objects_with_notifications, objects_without_notifications, event)
            end_time = datetime.datetime.now()
            elapsed_time = end_time - start_time
            logger.info(f'Finished listener_processing event '
                        f'of type {event["event_type"]} from {event["event_time"]} in {str(elapsed_time)}')

            return True, 'Success'


        # Connect to Redis
        event_bus = connect_to_hdx_event_bus_with_env_vars()
        # redis-py 8.0 introduced a default socket_timeout of 5s which causes xreadgroup(block=120_000ms ~= 120s)
        # to timeout prematurely. Set it above the block duration so only genuine hangs trigger it.
        event_bus.redis_conn.connection_pool.connection_kwargs['socket_timeout'] = 3 * 60
        logger.info('Connected to Redis')

        event_bus.hdx_listen(event_processor, allowed_event_types=ALLOWED_EVENT_TYPES, max_iterations=10_000)

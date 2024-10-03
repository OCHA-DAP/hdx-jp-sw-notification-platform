import datetime
import json
import logging.config

from hdx_redis_lib import connect_to_hdx_event_bus_with_env_vars

from config.config import get_config
from processing.datasets import get_dataset_id_list
from processing.helpers import ALLOWED_EVENT_TYPES
from processing.helpers import do_nothing_for_ever
from processing.main import process

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)


config = get_config()

dataset_id_list = get_dataset_id_list()

if __name__ == '__main__':
    if not config.WORKER_ENABLED:
        do_nothing_for_ever()

    else:

        def event_processor(event):
            logger.info('Received event: ' + json.dumps(event, ensure_ascii=False, indent=4))
            start_time = datetime.datetime.now()

            process(dataset_id_list, event)
            end_time = datetime.datetime.now()
            elapsed_time = end_time - start_time
            logger.info(f'Finished processing event '
                        f'of type {event["event_type"]} from {event["event_time"]} in {str(elapsed_time)}')

            return True, 'Success'


        # Connect to Redis
        event_bus = connect_to_hdx_event_bus_with_env_vars()
        logger.info('Connected to Redis')

        event_bus.hdx_listen(event_processor, allowed_event_types=ALLOWED_EVENT_TYPES, max_iterations=10_000)

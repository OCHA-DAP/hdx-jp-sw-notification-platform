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
from common.db_utils import test_db, init_db  # noqa
from common.model import DatasetToUser  # noqa
from common.db_utils import db_session  # noqa
from common.model import generate_object_hash_id  # noqa

from sync_processing.main import process_dataset_to_user

logger = logging.getLogger(__name__)


config = get_config()

objects_with_notifications = get_objects_with_notifications()
objects_without_notifications = get_objects_without_notifications()
cache_time = datetime.datetime.now()


def add_test_data():


    session = db_session()
    rows = [
        {
            'id': generate_object_hash_id('user1', 'wfp', 'ds1', 'user1', 'sub1'),
            'dataset_id': 'ds1',
            'object_id': 'wfp',
            'object_type': 'organization',
            'user_id': 'user1',
            'subscription_id': 'sub1',
            'event_type': 'dataset-updated',
            'tid_hash': generate_object_hash_id('user1', 'wfp', 'ds1'),
        },
        {
            'id': generate_object_hash_id('user1', 'wfp', 'ds2', 'user1', 'sub1'),
            'dataset_id': 'ds2',
            'object_id': 'wfp',
            'object_type': 'organization',
            'user_id': 'user1',
            'subscription_id': 'sub1',
            'event_type': 'dataset-updated',
            'tid_hash': generate_object_hash_id('user1', 'wfp', 'ds2'),
        },
        {
            'id': generate_object_hash_id('user1', 'wfp', 'ds3', 'user1', 'sub1'),
            'dataset_id': 'ds3',
            'object_id': 'wfp',
            'object_type': 'organization',
            'user_id': 'user1',
            'subscription_id': 'sub1',
            'event_type': 'dataset-updated',
            'tid_hash': generate_object_hash_id('user1', 'wfp', 'ds3'),
        },
        {
            'id': generate_object_hash_id('user1', 'wfp', 'ds4', 'user1', 'sub1'),
            'dataset_id': 'ds4',
            'object_id': 'wfp',
            'object_type': 'organization',
            'user_id': 'user1',
            'subscription_id': 'sub1',
            'event_type': 'dataset-updated',
            'tid_hash': generate_object_hash_id('user1', 'wfp', 'ds4'),
        },
    ]
    try:
        DatasetToUser.bulk_insert_from_dicts(session, rows)
        print('Inserted rows successfully.')
    except Exception as e:
        print(f'Failed to insert rows: {e}')
    finally:
        session.close()  # Always close the session


if __name__ == '__main__':

    test_db()
    init_db()
    # add_test_data()
    process_dataset_to_user()



    print('done')

    # if not config.WORKER_ENABLED:
    #     do_nothing_for_ever()
    # else:
    #
    #     def event_processor(event):
    #         global objects_with_notifications
    #         global objects_without_notifications
    #         global cache_time
    #
    #         logger.info('Received event: ' + json.dumps(event, ensure_ascii=False, indent=4))
    #         start_time = datetime.datetime.now()
    #         if is_cached_expired(start_time, cache_time):
    #             objects_with_notifications = get_objects_with_notifications(is_expired=True)
    #             objects_without_notifications = get_objects_without_notifications(is_expired=True)
    #             cache_time = datetime.datetime.now()
    #         process(objects_with_notifications, objects_without_notifications, event)
    #         end_time = datetime.datetime.now()
    #         elapsed_time = end_time - start_time
    #         logger.info(f'Finished listener_processing event '
    #                     f'of type {event["event_type"]} from {event["event_time"]} in {str(elapsed_time)}')
    #
    #         return True, 'Success'
    #
    #
    #     # Connect to Redis
    #     event_bus = connect_to_hdx_event_bus_with_env_vars()
    #     logger.info('Connected to Redis')
    #
    #     event_bus.hdx_listen(event_processor, allowed_event_types=ALLOWED_EVENT_TYPES, max_iterations=10_000)

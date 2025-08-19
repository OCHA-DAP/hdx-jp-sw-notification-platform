import logging.config

logging.config.fileConfig('logging.conf')

import datetime  # noqa
from config.config import get_config  # noqa
from listener_processing.objects import get_objects_with_notifications, get_objects_without_notifications  # noqa
from common.db_utils import test_db, init_db  # noqa
from sync_processing.main import process_dataset_to_user # noqa

logger = logging.getLogger(__name__)


config = get_config()

objects_with_notifications = get_objects_with_notifications()
objects_without_notifications = get_objects_without_notifications()
cache_time = datetime.datetime.now()


# def add_test_data():


#     session = db_session()
#     rows = [
#         {
#             'id': generate_object_hash_id('user1', 'wfp', 'ds1', 'user1', 'sub1'),
#             'dataset_id': 'ds1',
#             'object_id': 'wfp',
#             'object_type': 'organization',
#             'user_id': 'user1',
#             'subscription_id': 'sub1',
#             'event_type': 'dataset-updated',
#             'tid_hash': generate_object_hash_id('user1', 'wfp', 'ds1'),
#         },
#         {
#             'id': generate_object_hash_id('user1', 'wfp', 'ds2', 'user1', 'sub1'),
#             'dataset_id': 'ds2',
#             'object_id': 'wfp',
#             'object_type': 'organization',
#             'user_id': 'user1',
#             'subscription_id': 'sub1',
#             'event_type': 'dataset-updated',
#             'tid_hash': generate_object_hash_id('user1', 'wfp', 'ds2'),
#         },
#         {
#             'id': generate_object_hash_id('user1', 'wfp', 'ds3', 'user1', 'sub1'),
#             'dataset_id': 'ds3',
#             'object_id': 'wfp',
#             'object_type': 'organization',
#             'user_id': 'user1',
#             'subscription_id': 'sub1',
#             'event_type': 'dataset-updated',
#             'tid_hash': generate_object_hash_id('user1', 'wfp', 'ds3'),
#         },
#         {
#             'id': generate_object_hash_id('user1', 'wfp', 'ds4', 'user1', 'sub1'),
#             'dataset_id': 'ds4',
#             'object_id': 'wfp',
#             'object_type': 'organization',
#             'user_id': 'user1',
#             'subscription_id': 'sub1',
#             'event_type': 'dataset-updated',
#             'tid_hash': generate_object_hash_id('user1', 'wfp', 'ds4'),
#         },
#     ]
#     try:
#         DatasetToUser.bulk_insert_from_dicts(session, rows)
#         print('Inserted rows successfully.')
#     except Exception as e:
#         print(f'Failed to insert rows: {e}')
#     finally:
#         session.close()  # Always close the session


if __name__ == '__main__':

    test_db()
    init_db()
    # add_test_data()
    process_dataset_to_user()

    print('done')

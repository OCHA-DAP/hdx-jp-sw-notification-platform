import datetime
import os
import logging

from common.model import DatasetToUser
from sync_processing.get import hdx_notifications_grouped_subscription_list, hdx_notifications_subscription_list, hdx_get_datasets_ids_by_object
from common.utils import generate_object_hash_id, compute_tid_hash_diff
from common.db_utils import db_session
from hdx_redis_lib import connect_to_hdx_write_only_event_bus, RedisConfig  # noqa

logger = logging.getLogger(__name__)

redis_stream_host = os.getenv('REDIS_STREAM_HOST', 'redis')
redis_stream_port = os.getenv('REDIS_STREAM_PORT', 6379)
redis_stream_db = os.getenv('REDIS_STREAM_DB', 7)

event_bus = connect_to_hdx_write_only_event_bus(
    'hdx_event_stream',
    RedisConfig(host=redis_stream_host, port=redis_stream_port, db=redis_stream_db)
)


def process_dataset_to_user():
    session = db_session()

    # Define the time frame for the last 3 days
    three_days_ago = datetime.datetime.now() - datetime.timedelta(days=3)
    # Fetch subscriptions that are marked as not 'active' and modified in the last 3 days
    data_dict_deletion = {
        'active': False,
        'updated': three_days_ago
    }
    # Fetch the list of subscriptions for deletion
    subscriptions_for_deletion = hdx_notifications_subscription_list(data_dict_deletion)
    # Extract subscription IDs from the fetched subscriptions
    subscription_ids_to_delete = [sub['id'] for sub in subscriptions_for_deletion]
    DatasetToUser.delete_by_subscription_ids(session, subscription_ids_to_delete)

    ckan_subscriptions = hdx_notifications_grouped_subscription_list()
    for ckan_subscription in ckan_subscriptions:
        object_id = ckan_subscription.get('object', '')
        object_type = ckan_subscription.get('object_type', '')
        user_list = ckan_subscription.get('user_list', [])

        object_datasets = hdx_get_datasets_ids_by_object({'object_type': object_type, 'object_id': object_id})
        ckan_subscription['dataset_list'] = object_datasets

        if user_list:
            notify_subscription = DatasetToUser.get_by_subscription_id(
                session, subscription_id=user_list[0].get('subscription_id')
            )
        else:
            notify_subscription = None

        sets = compute_tid_hash_diff(ckan_subscription, notify_subscription)
        to_be_inserted = sets[0]
        to_be_deleted = sets[1]
        DatasetToUser.delete_by_tid_hash_list(session, tid_hash_list=to_be_deleted)

        datasets_to_be_inserted = [
           d for d in ckan_subscription.get('dataset_list', []) if d['tid_hash'] in to_be_inserted
        ]

        # Add the event to the Redis stream
        event_type = f'{object_type}-dataset-added'
        event = {
            'event_type': event_type,
            'event_time': datetime.now().isoformat(),
            'event_source': 'ckan',
            'object_type': object_type,
            'object_id': object_id,
            'dataset_list': to_be_inserted,
        }
        logger.info('Processing event type {}'.format(event['event_type']))
        event_bus.push_hdx_event(event)
        logger.info('Finished processing event type {}'.format(event['event_type']))

        for user in ckan_subscription.get('user_list'):
            user_id = user.get('user_id', '')
            subscription_id = user.get('subscription_id', '')
            event_type = user.get('event_type', '')
            objects_to_be_inserted = []

            for dataset in datasets_to_be_inserted:
                dataset_id = dataset['id']
                dataset_hash = dataset['tid_hash']
                entry = {
                    'id': generate_object_hash_id(object_type, object_id, dataset_id, subscription_id),
                    'dataset_id': dataset_id,
                    'object_id': object_id,
                    'object_type': object_type,
                    'user_id': user_id,
                    'subscription_id': subscription_id,
                    'event_type': event_type,
                    'tid_hash': dataset_hash,
                }
                objects_to_be_inserted.append(entry)

            if objects_to_be_inserted:
                DatasetToUser.bulk_insert_from_dicts(session, objects_to_be_inserted)

        session.commit()

    pass

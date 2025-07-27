import datetime
import os
import logging
import uuid

from common.model import NotifyObject, Dataset, Subscription
from sync_processing.get import (
    hdx_notifications_grouped_subscription_list,
    hdx_notifications_subscription_list,
    hdx_get_datasets_ids_by_object
)
from common.utils import compute_tid_hash_diff
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
    """
    sync process using the 3-table schema:
    - object: stores object information
    - dataset: stores dataset information with foreign key to object
    - subscription: stores subscription information with foreign key to object
    """
    session = db_session()

    try:
        # Step 1: Clean up inactive subscriptions from the last 3 days
        three_days_ago = datetime.datetime.now() - datetime.timedelta(days=3)
        data_dict_deletion = {
            'active': False,
            'updated': three_days_ago
        }

        subscriptions_for_deletion = hdx_notifications_subscription_list(data_dict_deletion)
        subscription_ids_to_delete = [uuid.UUID(sub['id']) for sub in subscriptions_for_deletion]

        if subscription_ids_to_delete:
            Subscription.delete_by_ids(session, subscription_ids_to_delete)
            logger.info(f'Deleted {len(subscription_ids_to_delete)} inactive subscriptions')


       # Clean up objects with no subscriptions
        orphaned_count = NotifyObject.delete_objects_with_no_subscriptions(session)
        if orphaned_count > 0:
            logger.info(f'Deleted {orphaned_count} orphaned objects')

        session.commit()

        # Step 2: Process active subscriptions grouped by object
        ckan_subscriptions = hdx_notifications_grouped_subscription_list()

        for ckan_subscription in ckan_subscriptions:
            object_id = ckan_subscription.get('object', '')
            object_type = ckan_subscription.get('object_type', '')
            user_list = ckan_subscription.get('user_list', [])

            if not object_id or not object_type:
                logger.warning(f'Skipping subscription with missing object info: {ckan_subscription}')
                continue

            # Step 3: Get or create the NotifyObject
            notify_object = NotifyObject.get_or_create(session, object_type, object_id)

            # Step 4: Get datasets for this object from CKAN
            object_datasets = hdx_get_datasets_ids_by_object({
                'object_type': object_type,
                'object_id': object_id
            })
            ckan_subscription['dataset_list'] = object_datasets

            # Step 5: Compare datasets and sync them
            existing_datasets = Dataset.get_by_notify_object_id(session, notify_object.id)
            to_be_inserted, to_be_deleted = compute_tid_hash_diff(ckan_subscription, existing_datasets)

            # Delete outdated datasets
            if to_be_deleted:
                Dataset.delete_by_ids(session, list(to_be_deleted))
                logger.info(f'Deleted {len(to_be_deleted)} outdated datasets for object {object_id}')

            # Prepare datasets to be inserted
            datasets_to_be_inserted = [
                d for d in ckan_subscription.get('dataset_list', [])
                if d['tid_hash'] in to_be_inserted
            ]

            # Insert new datasets
            if datasets_to_be_inserted:
                dataset_entries = []
                for dataset in datasets_to_be_inserted:
                    dataset_entries.append({
                        'id': dataset['tid_hash'],
                        'dataset_id': dataset['id'],
                        'notify_object_id': notify_object.id,
                    })
                Dataset.bulk_insert_from_dicts(session, dataset_entries)
                logger.info(f'Inserted {len(dataset_entries)} new datasets for object {object_id}')

            # Step 6: Sync subscriptions
            existing_subscriptions = Subscription.get_by_notify_object_id(session, notify_object.id)
            existing_subscription_ids = {str(sub.id) for sub in existing_subscriptions}
            ckan_subscription_ids = {user.get('subscription_id') for user in user_list}

            # Delete obsolete subscriptions
            subscriptions_to_delete = existing_subscription_ids - ckan_subscription_ids
            if subscriptions_to_delete:
                subscription_uuids = [uuid.UUID(sub_id) for sub_id in subscriptions_to_delete]
                Subscription.delete_by_ids(session, subscription_uuids)
                logger.info(f'Deleted {len(subscriptions_to_delete)} obsolete subscriptions for object {object_id}')

            # Insert new subscriptions
            subscriptions_to_insert = ckan_subscription_ids - existing_subscription_ids
            if subscriptions_to_insert:
                subscription_entries = []
                for user in user_list:
                    subscription_id = user.get('subscription_id')
                    if subscription_id in subscriptions_to_insert:
                        subscription_entries.append({
                            'id': uuid.UUID(subscription_id),
                            'user_id': user.get('user_id', ''),
                            'event_type': user.get('event_type', ''),
                            'notify_object_id': notify_object.id,
                        })

                if subscription_entries:
                    Subscription.bulk_insert_from_dicts(session, subscription_entries)
                    logger.info(f'Inserted {len(subscription_entries)} new subscriptions for object {object_id}')

            # Step 7: Push event to Redis if there were dataset changes
            if False:
                _push_to_event_bus(object_id, object_type, datasets_to_be_inserted)

        # Commit all changes
        session.commit()
        logger.info('Sync process completed successfully')

    except Exception as e:
        session.rollback()
        logger.error(f'Error during sync process: {e}')
        raise
    finally:
        session.close()


def _push_to_event_bus(object_id, object_type, datasets_to_be_inserted):
    """Push event to Redis event bus when datasets are added"""
    event_type = f'{object_type}-dataset-added'
    event = {
        'event_type': event_type,
        'event_time': datetime.datetime.now().isoformat(),
        'event_source': 'ckan',
        'object_type': object_type,
        'object_id': object_id,
        'dataset_list': datasets_to_be_inserted,
    }
    logger.info('Processing event type {}'.format(event['event_type']))
    event_bus.push_hdx_event(event)
    logger.info('Finished processing event type {}'.format(event['event_type']))

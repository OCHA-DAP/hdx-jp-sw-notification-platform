import datetime

from common.model import DatasetToUser
from sync_processing.get import hdx_notifications_grouped_subscription_list, hdx_notifications_subscription_list, hdx_get_datasets_ids_by_object
from common.utils import generate_object_hash_id, compute_tid_hash_diff
from common.db_utils import db_session


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
        data_dict = {'object_type': ckan_subscription.get('object_type'), 'object_id': ckan_subscription.get('object')}
        object_datasets = hdx_get_datasets_ids_by_object(data_dict)
        ckan_subscription['dataset_list'] = object_datasets

        user_list = ckan_subscription.get('user_list', [])
        if user_list:
            notify_subscription = DatasetToUser.get_by_subscription_id(session, subscription_id=user_list[0].get('subscription_id'))
        else:
            notify_subscription = None

        sets = compute_tid_hash_diff(ckan_subscription, notify_subscription)
        to_be_deleted = sets[1]
        to_be_inserted = sets[0]
        DatasetToUser.delete_by_tid_hash_list(session, tid_hash_list=to_be_deleted)

        for user in ckan_subscription.get('user_list'):
            objects_to_be_inserted = []

            for dataset in ckan_subscription.get('dataset_list', []):
                if dataset['tid_hash'] in to_be_inserted:
                    object_type = ckan_subscription.get('object_type', '')
                    object_id = ckan_subscription.get('object', '')
                    dataset_id = dataset['id']
                    subscription_id = user['subscription_id']
                    entry = {
                        'id': generate_object_hash_id(object_type, object_id, dataset_id, subscription_id),
                        'dataset_id': dataset_id,
                        'object_id': object_id,
                        'object_type': object_type,
                        'user_id': user['user_id'],
                        'subscription_id': subscription_id,
                        'event_type': user.get('event_type', ''),
                        'tid_hash': dataset['tid_hash'],
                    }
                    objects_to_be_inserted.append(entry)

            if objects_to_be_inserted:
                DatasetToUser.bulk_insert_from_dicts(session, objects_to_be_inserted)

        session.commit()

    pass

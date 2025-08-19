import hashlib
from typing import Optional

def generate_hash(*parts: str) -> str:
    key = ':'.join(parts)
    return hashlib.md5(key.encode('utf-8')).hexdigest()

def generate_object_hash_id(
    object_type: str,
    object_id: str,
    dataset_id: str,
    subscription_id: Optional[str] = ''
) -> str:
    return generate_hash(object_type,object_id, dataset_id, subscription_id)


def compute_dataset_diff(subscription_from_ckan, datasets_from_notify):
    """
    Compare datasets between CKAN subscription and existing notify datasets.
    Returns datasets to insert and dataset IDs to delete.
    Note that Dataset.id is the tid_hash.
    """
    # 1. Extract dataset IDs from CKAN subscription
    ckan_dataset_ids = set()
    object_id = subscription_from_ckan['object']
    object_type = subscription_from_ckan['object_type']

    for dataset in subscription_from_ckan['dataset_list']:
        dataset_id = dataset.get('id')
        tid_hash = generate_object_hash_id(object_type, object_id, dataset_id)
        dataset['tid_hash'] = tid_hash
        ckan_dataset_ids.add(tid_hash)

    # 2. Extract dataset IDs from existing notify datasets (using the id field which is the tid_hash)
    notify_dataset_ids = {dataset.id for dataset in datasets_from_notify}

    # 3. Set operations
    to_be_inserted = ckan_dataset_ids - notify_dataset_ids
    to_be_deleted = notify_dataset_ids - ckan_dataset_ids

    return to_be_inserted, to_be_deleted

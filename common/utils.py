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


def compute_tid_hash_diff(subscription_from_ckan, subscription_from_notify):
    # 1. Extract tid_hashes from CKAN subscription
    ckan_tid_hashes = set()
    object_id = subscription_from_ckan['object']
    object_type = subscription_from_ckan['object_type']
    for dataset in subscription_from_ckan['dataset_list']:
        dataset_id = dataset.get('id')
        tid = generate_object_hash_id(object_type, object_id, dataset_id)
        dataset['tid_hash'] = tid
        ckan_tid_hashes.add(tid)

    # 2. Extract tid_hashes from Notify subscription
    notify_tid_hashes = {row.tid_hash for row in subscription_from_notify}

    # 3. Set operations
    a_minus_b = ckan_tid_hashes - notify_tid_hashes
    b_minus_a = notify_tid_hashes - ckan_tid_hashes

    return a_minus_b, b_minus_a

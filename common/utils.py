import hashlib
from typing import Optional

def generate_hash(*parts: str) -> str:
    key = ':'.join(parts)
    return hashlib.md5(key.encode('utf-8')).hexdigest()

def generate_object_hash_id(
    object_type: str,
    object_id: str,
    dataset_id: str,
    user_id: Optional[str] = '',
    subscription_id: Optional[str] = ''
) -> str:
    return generate_hash(object_type,object_id, dataset_id, user_id, subscription_id)


def compute_tid_hash_diff(set_a, set_b):
    # 1. Extract tid_hashes from set_a
    a_tid_hashes = set()
    for entry in set_a:
        object_id = entry['object']
        object_type = entry['object_type']
        for user in entry['user_list']:
            user_id = user['user_id']
            for dataset_id in entry['dataset_list']:
                tid = generate_object_hash_id(user_id, object_id, dataset_id)
                a_tid_hashes.add(tid)

    # 2. Extract tid_hashes from set_b
    b_tid_hashes = {row['tid_hash'] for row in set_b}

    # 3. Set operations
    a_minus_b = a_tid_hashes - b_tid_hashes
    b_minus_a = b_tid_hashes - a_tid_hashes

    return a_minus_b, b_minus_a

from common.model import DatasetToUser
from sync_processing.get import hdx_notifications_subscription_list, hdx_get_datasets_ids_by_object
from common.utils import generate_object_hash_id, compute_tid_hash_diff
from common.db_utils import db_session


CKAN_DUMMY_DATA = [
        {
            'object': 'wfp',
            'object_type': 'organization',
            'query_params': '',
            'user_list': [
                {
                    'user_id':'user1',
                    'subscription_id':'sub1',
                    'event_type':'dataset-updated',
                }
            ],
            'dataset_list': ['ds3','ds4','ds5','ds6']
        },

    ]


def process_dataset_to_user():


    # TODO select * subscriptions where state = 'deleted' and modified in last 3 days=> delete from dataset to user where sub_id=sub_id
    # subscription_list = ['sub1', 'sub2']
    # session = db_session()
    # DatasetToUser.delete_by_subscription_ids(session, subscription_list)

    # read all notif data from ckan db
    hdx_notif_sub_list = hdx_notifications_subscription_list({})
    print('hdx_notif_sub_list: done')

    #TODO run query on ckan to get list of datasets_ids - do it in ckan - wrap over package_search - don't include private, archived, fl param
    # for each notif in hdx_notif_sub_list
        # dataset_id_list = hdx_get_datasets_ids_by_object({'object_type':'organization', 'object_id':'acaps'})
        # add list to notif item -> e.g. CKAN_DUMMY_DATA

    compute_tid_hash_diff(CKAN_DUMMY_DATA, hdx_notif_sub_list)

    #DatasetToUser.delete_by_tid_hash_list(session, tid_hash_list=tid_hash_list)

    # records = DatasetToUser.get_by_tid_hash(session, tid_hash)



    # get set1 - from notify db
    # set2 - ckan db
    # set3 = set1 - set2 data to be deleted from notify db
    # set4 = set2 - set1 data to be inserted in notify db
    # delete from notify db set3
    # insert into notify db set4
    pass

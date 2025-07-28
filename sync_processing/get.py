import datetime
import os
import requests
from typing import Dict, Any, List, Optional
from config.config import get_config

config = get_config()

def hdx_action(url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get the list of dataset names (packages) from HDX using the CKAN API with authentication.
    Requires HDX_API_KEY to be set in environment variables.
    """
    # if not config.HDX_API_KEY:
    #     raise ValueError('HDX_API_KEY environment variable not set')

    headers = {
        'Authorization': config.HDX_API_KEY
    }
    # url = config.HDX_URL + config.HDX_PKG_SEARCH_URL
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Raise an error for bad responses

    data = response.json()
    if not data.get('success'):
        raise RuntimeError('API call failed: ' + str(data))

    return data['result']

def hdx_package_search(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = config.HDX_URL + config.HDX_PKG_SEARCH_URL
    return hdx_action(url, params)


def get_all_subscriptions(updated: Optional[datetime.datetime] = None, active: Optional[bool] = True, page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch all notification subscriptions from HDX.
    Requires API key with sysadmin privileges.

    Args:
        updated (Optional[datetime.datetime]): Filter subscriptions modified on or after this datetime.
        active (Optional[bool]): Fetch 'active' subscriptions if True; fetch non-active ones if False. Defaults to True.
        page_size (int): The number of subscriptions per page. Defaults to 100.

    Returns:
        List[Dict[str, Any]]: A list of subscription dictionaries.
    """
    all_subscriptions = []
    page = 1

    while True:
        params = {
            'updated': updated.isoformat() if updated is not None else None,
            'active': active,
            'page': page,
            'page_size': page_size
        }

        url = f'{config.HDX_URL}{config.HDX_NOTIFICATIONS_SUBCRIPTION_LIST_URL}'
        headers = {'Authorization': config.HDX_API_KEY}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            raise RuntimeError(f'API call failed on page {page}: {data}')

        page_result = data.get('result', [])
        if not page_result:
            break  # no more data

        all_subscriptions.extend(page_result)
        page += 1

    return all_subscriptions


def get_grouped_subscriptions() -> List[Dict[str, Any]]:
    """
    Fetch grouped notification subscriptions from HDX.
    Requires API key with sysadmin privileges.

    Returns:
        List[Dict[str, Any]]: A list of subscription dictionaries.
    """
    all_subscriptions = []

    url = f'{config.HDX_URL}{config.HDX_NOTIFICATIONS_GROUPED_SUBCRIPTION_LIST_URL}'
    headers = {'Authorization': config.HDX_API_KEY}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if not data.get('success'):
        raise RuntimeError(f'API call failed on page {page}: {data}')

    page_result = data.get('result', [])

    all_subscriptions.extend(page_result)

    return all_subscriptions


def hdx_notifications_subscription_list(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return a list of notification subscriptions.

    Args:
        params (Dict[str, Any]): A dictionary containing parameters for fetching subscriptions.
            - updated (Optional[datetime.datetime]): Filter subscriptions modified on or after this datetime.
            - active (Optional[bool]): Fetch 'active' subscriptions if True; fetch non-active ones if False. Defaults to True.

    Returns:
        List[Dict[str, Any]]: A list of subscription dictionaries.
    """
    active = params.get('active', True)
    updated = params.get('updated', None)

    return get_all_subscriptions(active=active, updated=updated)


def hdx_notifications_grouped_subscription_list():
    """
    Return a list of active subscriptions grouped by object and object_type

    Returns:
        List[Dict[str, Any]]: A list of subscription dictionaries.
    """
    return get_grouped_subscriptions()


def hdx_get_datasets_ids_by_object(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    if params.get('object_type') == 'dataset':
        return [{'id': params.get('object_id')}]
    else:
        url = config.HDX_URL + config.HDX_DATASETS_IDS_BY_OBJECT_URL
        return hdx_action(url, params)

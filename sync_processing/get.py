import os
import requests
from typing import Dict, Any, List
from config.config import get_config

config = get_config()

def hdx_action(url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get the list of dataset names (packages) from HDX using the CKAN API with authentication.
    Requires HDX_API_KEY to be set in environment variables.
    """
    # if not config.HDX_API_KEY:
    #     raise ValueError("HDX_API_KEY environment variable not set")

    headers = {
        'Authorization': config.HDX_API_KEY
    }
    # url = config.HDX_URL + config.HDX_PKG_SEARCH_URL
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Raise an error for bad responses

    data = response.json()
    if not data.get('success'):
        raise RuntimeError("API call failed: " + str(data))

    return data['result']

def hdx_package_search(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = config.HDX_URL + config.HDX_PKG_SEARCH_URL
    return hdx_action(url, params)


def get_all_subscriptions(page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch all notification subscriptions from HDX.
    Requires API key with sysadmin privileges.
    """
    all_subscriptions = []
    page = 1

    while True:
        params = {
            "page": page,
            "page_size": page_size
        }

        url = f"{config.HDX_URL}{config.HDX_NOTIFICATIONS_SUBCRIPTION_LIST_URL}"
        headers = {'Authorization': config.HDX_API_KEY}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise RuntimeError(f"API call failed on page {page}: {data}")

        page_result = data.get("result", [])
        if not page_result:
            break  # no more data

        all_subscriptions.extend(page_result)
        page += 1

    return all_subscriptions


def hdx_notifications_subscription_list(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    return get_all_subscriptions()


def hdx_get_datasets_ids_by_object(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = config.HDX_URL + config.HDX_DATASETS_IDS_BY_OBJECT_URL
    return hdx_action(url, params)

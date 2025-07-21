import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Config:
    WORKER_ENABLED: bool
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    HDX_ENABLED_DATASETS_CSV: str
    NOVU_API_KEY: str
    NOVU_API_URL: str
    HDX_URL: str
    HDX_DATASETS_CSV_EXPIRATION_HOURS: str
    HDX_PKG_SEARCH_URL: str
    HDX_API_KEY: str
    HDX_NOTIFICATIONS_SUBCRIPTION_LIST_URL: str
    HDX_NOTIFICATIONS_GROUPED_SUBCRIPTION_LIST_URL: str
    HDX_DATASETS_IDS_BY_OBJECT_URL: str


CONFIG = None

def get_config() -> Config:
    global CONFIG
    if not CONFIG:
        CONFIG = Config(
            WORKER_ENABLED=os.getenv('WORKER_ENABLED') == 'true',
            DB_USER=os.getenv('DB_USER', 'notify'),
            DB_PASS=os.getenv('DB_PASS', 'notify'),
            DB_HOST=os.getenv('DB_HOST', 'db'),
            DB_PORT=os.getenv('DB_PORT', '5432'),
            DB_NAME=os.getenv('DB_NAME', 'notify'),
            HDX_ENABLED_DATASETS_CSV=os.getenv(
                'HDX_ENABLED_DATASETS_CSV',
                'https://docs.google.com/spreadsheets/d/e/2PACX-1vSsBSUTM3f9olyhVFDcAh-tXV63wlOtvsXukQIHTLiLCfbGJC8osDDaEqzoUVs2B0kgYMrkyVkihvVm/pub?gid=0&single=true&output=csv',
            ),
            HDX_DATASETS_CSV_EXPIRATION_HOURS=os.getenv('HDX_DATASETS_CSV_EXPIRATION_HOURS', '1'),
            NOVU_API_KEY=os.getenv('NOVU_API_KEY'),
            NOVU_API_URL=os.getenv('NOVU_API_URL', 'https://api.novu.co/v1/events/trigger'),
            #TODO
            HDX_URL= os.getenv('HDX_URL', 'https://data.humdata.local'),
            HDX_PKG_SEARCH_URL=os.getenv('HDX_PKG_SEARCH_URL', '/api/3/action/package_search'),
            HDX_NOTIFICATIONS_SUBCRIPTION_LIST_URL=os.getenv(
                'HDX_NOTIFICATIONS_SUBCRIPTION_LIST_URL', '/api/3/action/hdx_notifications_subscription_list'
            ),
            HDX_NOTIFICATIONS_GROUPED_SUBCRIPTION_LIST_URL=os.getenv(
                'HDX_NOTIFICATIONS_GROUPED_SUBCRIPTION_LIST_URL', '/api/3/action/hdx_notifications_grouped_subscription_list'
            ),
            HDX_API_KEY=os.getenv('HDX_API_KEY', ''),
            HDX_DATASETS_IDS_BY_OBJECT_URL=os.getenv(
                'HDX_DATASETS_IDS_BY_OBJECT_URL', '/api/3/action/hdx_search_by_object'
            ),
        )

    return CONFIG

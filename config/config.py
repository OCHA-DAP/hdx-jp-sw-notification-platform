import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Config:
    WORKER_ENABLED: bool
    GOOGLE_SHEETS_DATASET_ID_LIST_URL: str
    NOVU_API_KEY: str
    NOVU_API_URL: str


CONFIG = None


def get_config() -> Config:
    global CONFIG
    if not CONFIG:
        CONFIG = Config(
            WORKER_ENABLED=os.getenv('WORKER_ENABLED') == 'true',
            GOOGLE_SHEETS_DATASET_ID_LIST_URL=os.getenv('GOOGLE_SHEETS_DATASET_ID_LIST_URL',
                                                        'https://docs.google.com/spreadsheets/d/e/2PACX-1vSsBSUTM3f9olyhVFDcAh-tXV63wlOtvsXukQIHTLiLCfbGJC8osDDaEqzoUVs2B0kgYMrkyVkihvVm/pub?gid=0&single=true&output=csv'),
            NOVU_API_KEY=os.getenv('NOVU_API_KEY'),
            NOVU_API_URL=os.getenv('NOVU_API_URL', 'https://api.novu.co/v1/events/trigger'),
        )

    return CONFIG

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Config:
    WORKER_ENABLED: bool
    HDX_ENABLED_DATASETS_CSV: str
    NOVU_API_KEY: str
    NOVU_API_URL: str
    HDX_URL: str


CONFIG = None

def get_config() -> Config:
    global CONFIG
    if not CONFIG:
        CONFIG = Config(
            WORKER_ENABLED=os.getenv('WORKER_ENABLED') == 'true',
            HDX_ENABLED_DATASETS_CSV=os.getenv('HDX_ENABLED_DATASETS_CSV',
                                                        'https://docs.google.com/spreadsheets/d/e/2PACX-1vSsBSUTM3f9olyhVFDcAh-tXV63wlOtvsXukQIHTLiLCfbGJC8osDDaEqzoUVs2B0kgYMrkyVkihvVm/pub?gid=0&single=true&output=csv'),
            NOVU_API_KEY=os.getenv('NOVU_API_KEY'),
            NOVU_API_URL=os.getenv('NOVU_API_URL', 'https://api.novu.co/v1/events/trigger'),
            HDX_URL= os.getenv('HDX_URL', 'https://stage.data-humdata-org.ahconu.org'),
        )

    return CONFIG

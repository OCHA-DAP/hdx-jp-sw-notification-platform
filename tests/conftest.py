import pytest
import os

from config.config import Config, get_config

DEFAULT_ENV = {
    # 'REDIS_STREAM_HOST': 'gisredis',
    'REDIS_STREAM_DB': '14'
}


@pytest.fixture(scope='module', autouse=True)
def prepare_environment():
    for key, value in DEFAULT_ENV.items():
        os.environ[key] = value


#
# @pytest.fixture(scope='module')
# def key_value_store() -> RedisKeyValueStore:
#     key_value_store = connect_to_key_value_store_with_env_vars()
#     return key_value_store


@pytest.fixture(scope='module')
def config() -> Config:
    config = get_config()
    return config

# @pytest.fixture(scope='module')
# def context(key_value_store: RedisKeyValueStore, config: Config) -> Context:
#     context = Context(store=key_value_store, config=config, gsheets=None,  slack_client=SlackClientWrapper())
#     return context

# @pytest.fixture(scope='function')
# def clean_redis(key_value_store: RedisKeyValueStore) -> None:
#     key_value_store.redis_conn.flushdb()

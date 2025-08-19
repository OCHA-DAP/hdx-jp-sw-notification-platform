import pytest
import os

from mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.config import Config, get_config
from common.model import Base

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


@pytest.fixture(scope='function')
def db_session_for_testing():
    """Create a test database session for each test"""

    config = get_config()
    if not config.HDX_NOTIFICATIONSDB_DB.endswith('_test'):
        # Append '_test' to the database name for testing
        config.HDX_NOTIFICATIONSDB_DB = f'{config.HDX_NOTIFICATIONSDB_DB}_test'

    # Connect to the test database
    test_database_url = f'postgresql://{config.HDX_NOTIFICATIONSDB_USER}:{config.HDX_NOTIFICATIONSDB_PASS}@{config.HDX_NOTIFICATIONSDB_ADDR}:{config.HDX_NOTIFICATIONSDB_PORT}/{config.HDX_NOTIFICATIONSDB_DB}'
    test_engine = create_engine(test_database_url)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    session = TestSessionLocal()

    try:
        # Patch the global session and engine
        with patch('common.db_utils.SESSION', session), \
             patch('common.db_utils._engine', test_engine), \
             patch('sync_processing.main.db_session', return_value=session):

            yield session
    finally:
        # Cleanup - truncate all tables for clean state between tests
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(text(f'TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE'))
        session.commit()
        session.close()
        test_engine.dispose()
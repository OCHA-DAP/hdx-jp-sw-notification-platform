from unittest.mock import MagicMock, patch

from common.db_utils import INIT_LOCK_KEY, init_db


@patch('common.db_utils.Base.metadata.create_all')
def test_init_db_creates_tables_while_holding_the_lock(mock_create_all):
    """DATASET_NOTIFICATIONS-024"""
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    order = MagicMock()
    order.attach_mock(connection.execute, 'execute')
    order.attach_mock(mock_create_all, 'create_all')

    with patch('common.db_utils._engine', engine):
        init_db()

    lock_statement, lock_params = connection.execute.call_args.args
    assert 'pg_advisory_xact_lock' in str(lock_statement)
    assert lock_params == {'key': INIT_LOCK_KEY}
    # the lock is taken first, in the same transaction that creates the tables
    assert [c[0] for c in order.mock_calls] == ['execute', 'create_all']
    mock_create_all.assert_called_once_with(bind=connection)
    engine.begin.return_value.__exit__.assert_called_once()


@patch('common.db_utils.Base.metadata.create_all')
@patch('common.db_utils.create_engine')
def test_init_db_creates_the_engine_when_missing(mock_create_engine, mock_create_all):
    with patch('common.db_utils._engine', None):
        init_db()

    mock_create_engine.assert_called_once()
    mock_create_all.assert_called_once()

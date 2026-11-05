import os
from unittest.mock import patch

import pytest

from config.config import get_config


def test_aggregation_settings_defaults():
    """DATASET_NOTIFICATIONS-010, -012"""
    with patch.dict(os.environ, {}, clear=True), patch('config.config.CONFIG', None):
        config = get_config()

    assert config.DATASET_EVENT_AGGREGATION_ENABLED is True
    assert config.DATASET_EVENT_QUIET_PERIOD_SECONDS == 300
    assert config.DATASET_EVENT_MAX_WAIT_SECONDS == 1800


def test_aggregation_settings_from_env():
    env = {
        'DATASET_EVENT_AGGREGATION_ENABLED': 'false',
        'DATASET_EVENT_QUIET_PERIOD_SECONDS': '60',
        'DATASET_EVENT_MAX_WAIT_SECONDS': '600',
    }
    with patch.dict(os.environ, env, clear=True), patch('config.config.CONFIG', None):
        config = get_config()

    assert config.DATASET_EVENT_AGGREGATION_ENABLED is False
    assert config.DATASET_EVENT_QUIET_PERIOD_SECONDS == 60
    assert config.DATASET_EVENT_MAX_WAIT_SECONDS == 600


@pytest.mark.parametrize('value', ['true', 'True', 'False', '1', ''])
def test_aggregation_stays_on_unless_exactly_false(value):
    """DATASET_NOTIFICATIONS-010: only the exact value 'false' turns aggregation off"""
    with patch.dict(os.environ, {'DATASET_EVENT_AGGREGATION_ENABLED': value}, clear=True), \
            patch('config.config.CONFIG', None):
        assert get_config().DATASET_EVENT_AGGREGATION_ENABLED is True

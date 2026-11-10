from unittest.mock import patch

import pytest

import data.db_connect as dbc
import states.sample_data as sd
from states.query import STATES_COLLECT


def test_check_test_db_ok():
    sd.check_test_db(sd.TEST_DB_PREFIX + 'anything')


def test_check_test_db_refuses_real_db():
    with pytest.raises(RuntimeError):
        sd.check_test_db(dbc.DEFAULT_DB)


def test_tests_use_test_db():
    sd.check_test_db(dbc.SE_DB)


@pytest.mark.parametrize('fn', [sd.clear_states, sd.seed_states,
                                sd.stored_states])
def test_refuses_real_db_before_touching_it(fn):
    with patch.object(dbc, 'SE_DB', dbc.DEFAULT_DB), \
            patch('data.db_connect.connect_db', autospec=True) as mock_conn:
        with pytest.raises(RuntimeError):
            fn()
    mock_conn.assert_not_called()


def test_seed_states():
    sd.clear_states()
    sd.seed_states()
    assert sd.stored_states() == sd.SAMPLE_STATES


def test_seed_states_replaces_existing():
    dbc.create(STATES_COLLECT, {sd.STATE_CODE: 'ZZ'})
    sd.seed_states()
    assert sd.stored_states() == sd.SAMPLE_STATES


def test_clear_states():
    sd.clear_states()
    assert sd.stored_states() == {}


def test_sample_states_keyed_by_code():
    for code, state in sd.SAMPLE_STATES.items():
        assert state[sd.STATE_CODE] == code

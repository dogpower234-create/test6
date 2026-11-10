import os
from unittest.mock import patch

import pytest

import states.fields as flds
import states.load as ld

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'raw_data',
                        'states.csv')

TEST_ROW = {
    ld.CSV_ABBREV: 'AL',
    ld.CSV_LATITUDE: '32.318231',
    ld.CSV_LONGITUDE: '-86.902298',
    ld.CSV_STATE: 'Alabama',
}


def test_load_states():
    rows = ld.load_states(CSV_PATH)
    assert len(rows) > 0
    for row in rows:
        assert set(row) == {ld.CSV_ABBREV, ld.CSV_LATITUDE,
                            ld.CSV_LONGITUDE, ld.CSV_STATE}


def test_row_to_state_renames_fields():
    state = ld.row_to_state(TEST_ROW)
    assert state[flds.STATE_CODE] == TEST_ROW[ld.CSV_ABBREV]
    assert state[flds.NAME] == TEST_ROW[ld.CSV_STATE]
    assert state[flds.LATITUDE] == float(TEST_ROW[ld.CSV_LATITUDE])
    assert state[flds.LONGITUDE] == float(TEST_ROW[ld.CSV_LONGITUDE])


def test_row_to_state_fills_missing_fields():
    state = ld.row_to_state(TEST_ROW)
    assert state[flds.POPULATION] == 0
    assert state[flds.AREA] == 0
    assert state[flds.CAPITAL] == ''


def test_row_to_state_has_every_dictionary_field():
    state = ld.row_to_state(TEST_ROW)
    assert set(flds.STATE_FLDS) <= set(state)


def test_row_to_state_bad_latitude():
    with pytest.raises(ValueError):
        ld.row_to_state({**TEST_ROW, ld.CSV_LATITUDE: 'north'})


@patch('data.db_connect.create', autospec=True)
@patch('data.db_connect.drop', autospec=True)
@patch('data.db_connect.connect_db', autospec=True)
def test_store_states(mock_connect, mock_drop, mock_create):
    states = [ld.row_to_state(TEST_ROW), ld.row_to_state(TEST_ROW)]
    assert ld.store_states(states) == len(states)
    mock_connect.assert_called_once_with()
    mock_drop.assert_called_once_with(ld.STATES_COLLECT)
    assert mock_create.call_count == len(states)
    mock_create.assert_called_with(ld.STATES_COLLECT, states[-1])


@patch('data.db_connect.create', autospec=True)
@patch('data.db_connect.drop', autospec=True)
@patch('data.db_connect.connect_db', autospec=True)
def test_store_states_drops_before_create(mock_connect, mock_drop,
                                          mock_create):
    calls = []
    mock_drop.side_effect = lambda *args: calls.append('drop')
    mock_create.side_effect = lambda *args: calls.append('create')
    ld.store_states([ld.row_to_state(TEST_ROW)])
    assert calls == ['drop', 'create']


@patch('states.load.store_states', autospec=True, return_value=52)
def test_main(mock_store, capsys):
    with patch.object(ld.sys, 'argv', ['load.py', CSV_PATH]):
        ld.main()
    stored = mock_store.call_args.args[0]
    assert len(stored) == len(ld.load_states(CSV_PATH))
    assert all(flds.STATE_CODE in state for state in stored)
    assert ld.STATES_COLLECT in capsys.readouterr().out


@patch('states.load.store_states', autospec=True)
def test_main_no_args(mock_store):
    with patch.object(ld.sys, 'argv', ['load.py']):
        with pytest.raises(SystemExit):
            ld.main()
    mock_store.assert_not_called()

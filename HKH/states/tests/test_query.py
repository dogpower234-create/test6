from unittest.mock import patch

import pytest

import counties.query as cqry
import data.db_connect as dbc
import states.query as qry
from states.sample_data import SAMPLE_STATES, stored_states
from states.sample_data import clear_states

TEST_ST = qry.TEST_STATE


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state(mock_is_db_up):
    assert qry.check_valid_state(**TEST_ST)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state_code_and_name_only(mock_is_db_up):
    assert qry.check_valid_state(TEST_ST[qry.STATE_CODE], TEST_ST[qry.NAME])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state_code_bad_pop(mock_is_db_up):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(**{qry.POPULATION: -23423}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state_code_with_bad_name(mock_is_db_up):
    with pytest.raises(ValueError):
        ret = qry.check_valid_state(TEST_ST[qry.STATE_CODE],
                                    '',
                                    TEST_ST[qry.POPULATION],
                                    TEST_ST[qry.CAPITAL],
                                    TEST_ST[qry.AREA],
                                    TEST_ST[qry.LATITUDE],
                                    TEST_ST[qry.LONGITUDE])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state_code_too_short(mock_is_db_up):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(**{qry.STATE_CODE: ''}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state_code_too_long(mock_is_db_up):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(
            **{qry.STATE_CODE: 'X' * qry.STATE_CODE_LEN * 2}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state_dup_code(mock_is_db_up):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(**{qry.STATE_CODE: 'AL'}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm, val', [
    (qry.POPULATION, 0),
    (qry.CAPITAL, ''),
    (qry.AREA, 0),
    (qry.LATITUDE, 0),
    (qry.LONGITUDE, 0),
])
def test_check_valid_state_default_ok(mock_is_db_up, fld_nm, val):
    assert qry.check_valid_state(**state_args(**{fld_nm: val}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('val', [None, 123])
def test_check_valid_state_bad_capital(mock_is_db_up, val):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(**{qry.CAPITAL: val}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('val', [-1, -0.5, '100', None])
def test_check_valid_state_bad_area(mock_is_db_up, val):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(**{qry.AREA: val}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('val', ['', None, 5])
def test_check_valid_state_bad_name(mock_is_db_up, val):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(**{qry.NAME: val}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_query(mock_is_db_up):
    states = qry.read()
    assert isinstance(states, dict)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_read_one(mock_is_db_up):
    assert qry.read_one('AL') == stored_states()['AL']


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_read_one_no_mongo_id(mock_is_db_up):
    assert dbc.MONGO_ID not in qry.read_one('AL')


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_read_one_missing(mock_is_db_up):
    assert 'ZZ' not in stored_states()
    assert qry.read_one('ZZ') is None


@pytest.fixture
def temp_state():
    yield TEST_ST
    with patch('states.query.is_db_up', return_value=True, autospec=True):
        qry.delete(TEST_ST[qry.STATE_CODE])


@pytest.fixture
def temp_state_in_db():
    with patch('states.query.is_db_up', return_value=True, autospec=True):
        qry.create(**TEST_ST)
    yield TEST_ST
    with patch('states.query.is_db_up', return_value=True, autospec=True):
        qry.delete(TEST_ST[qry.STATE_CODE])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create(mock_is_db_up, temp_state):
    ret = qry.create(**temp_state)
    assert ret[qry.NAME] == temp_state[qry.NAME]
    assert qry.exists(temp_state[qry.STATE_CODE])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_dup(mock_is_db_up, temp_state_in_db):
    with pytest.raises(ValueError):
        qry.create(**temp_state_in_db)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete(mock_is_db_up, temp_state_in_db):
    code = temp_state_in_db[qry.STATE_CODE]
    assert code in stored_states()
    deleted = qry.delete(code)
    assert deleted[qry.NAME] == temp_state_in_db[qry.NAME]
    assert code not in stored_states()
    assert not qry.exists(code)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_leaves_other_states(mock_is_db_up, temp_state_in_db):
    others = {k: v for k, v in stored_states().items()
              if k != temp_state_in_db[qry.STATE_CODE]}
    qry.delete(temp_state_in_db[qry.STATE_CODE])
    assert stored_states() == others


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_with_counties(mock_is_db_up):
    assert cqry.has_counties('AL')
    before = dict(stored_states()['AL'])
    with pytest.raises(ValueError):
        qry.delete('AL')
    assert stored_states()['AL'] == before


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_no_counties(mock_is_db_up, temp_state_in_db):
    code = temp_state_in_db[qry.STATE_CODE]
    assert qry.delete(code)[qry.NAME] == temp_state_in_db[qry.NAME]
    assert not qry.exists(code)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_after_counties_gone(mock_is_db_up, temp_state):
    code = temp_state[qry.STATE_CODE]
    qry.create(**temp_state)
    county = {**cqry.TEST_COUNTY, cqry.STATE_CODE: code}
    cqry.create(**county)
    with pytest.raises(ValueError):
        qry.delete(code)
    cqry.delete(code, county[qry.NAME])
    assert qry.delete(code)[qry.NAME] == temp_state[qry.NAME]
    assert not qry.exists(code)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_missing(mock_is_db_up):
    assert 'ZZ' not in stored_states()
    assert qry.delete('ZZ') is None


@patch('states.query.is_db_up', return_value=False, autospec=True)
def test_delete_db_down(mock_is_db_up, temp_state_in_db):
    assert qry.delete(temp_state_in_db[qry.STATE_CODE]) is None
    assert temp_state_in_db[qry.STATE_CODE] in stored_states()


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state_update_missing(mock_is_db_up):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(**{qry.STATE_CODE: 'ZZ'}),
                              is_update=True)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_check_valid_state_update_existing(mock_is_db_up):
    assert qry.check_valid_state(**state_args(**{qry.STATE_CODE: 'AL'}),
                                 is_update=True)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update(mock_is_db_up, temp_state_in_db):
    code = temp_state_in_db[qry.STATE_CODE]
    ret = qry.update(code, 'New Name', 2000000, 'New Capital', 60000.5,
                     33.5, -87.5)
    assert stored_states()[code] == {
        qry.STATE_CODE: code,
        qry.NAME: 'New Name',
        qry.POPULATION: 2000000,
        qry.CAPITAL: 'New Capital',
        qry.AREA: 60000.5,
        qry.LATITUDE: 33.5,
        qry.LONGITUDE: -87.5,
    }
    assert ret == stored_states()[code]


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_leaves_other_states(mock_is_db_up, temp_state_in_db):
    others = {k: dict(v) for k, v in stored_states().items()
              if k != temp_state_in_db[qry.STATE_CODE]}
    qry.update(temp_state_in_db[qry.STATE_CODE], 'N', 1, 'C', 1.0,
               0.0, 0.0)
    for code, data in others.items():
        assert stored_states()[code] == data


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_missing(mock_is_db_up):
    assert 'ZZ' not in stored_states()
    with pytest.raises(ValueError):
        qry.update('ZZ', 'N', 1, 'C', 1.0, 0.0, 0.0)
    assert 'ZZ' not in stored_states()


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_invalid_leaves_state_unchanged(mock_is_db_up,
                                               temp_state_in_db):
    code = temp_state_in_db[qry.STATE_CODE]
    before = dict(stored_states()[code])
    with pytest.raises(ValueError):
        qry.update(code, 'N', -1, 'C', 1.0, 0.0, 0.0)
    assert stored_states()[code] == before


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_db_down(mock_is_db_up, temp_state_in_db):
    code = temp_state_in_db[qry.STATE_CODE]
    before = dict(stored_states()[code])
    mock_is_db_up.return_value = False
    assert qry.update(code, 'N', 1, 'C', 1.0, 0.0, 0.0) is None
    assert stored_states()[code] == before


def test_create_db_down(temp_state):
    with patch('states.query.is_db_up', return_value=False, autospec=True):
        assert qry.create(**temp_state) is None
    assert temp_state[qry.STATE_CODE] not in stored_states()


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_needs_db_calls_fn_when_up(mock_is_db_up):
    @qry.needs_db
    def fn(x, y=0):
        return x + y
    assert fn(1, y=2) == 3


def test_needs_db_returns_none_when_down():
    calls = []

    @qry.needs_db
    def fn():
        calls.append(1)
        return 'called'
    with patch('states.query.is_db_up', return_value=False, autospec=True):
        assert fn() is None
    assert calls == []


def test_needs_db_keeps_name():
    assert qry.create.__name__ == 'create'
    assert 'Create a new state' in qry.create.__doc__


@pytest.mark.parametrize('fn, args', [
    (qry.read, ()),
    (qry.exists, ('AL',)),
    (qry.read_one, ('AL',)),
    (qry.delete, ('AL',)),
])
def test_db_down_returns_none(fn, args):
    before = dict(stored_states())
    with patch('states.query.is_db_up', return_value=False, autospec=True):
        assert fn(*args) is None
    assert stored_states() == before


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_main(mock_is_db_up, capsys):
    qry.main()
    out = capsys.readouterr().out
    for code in stored_states():
        assert f'State: {code}' in out


@pytest.mark.parametrize('val, expected', [
    (1, True),
    (1.5, True),
    (-2, True),
    (True, False),
    ('1', False),
    (None, False),
])
def test_is_number(val, expected):
    assert qry.is_number(val) is expected


def state_args(**changes):
    """
    Return TEST_STATE's fields as check_valid_state arguments,
    with any given changes (keyed by field name) applied.
    """
    return {**TEST_ST, **changes}


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm, val', [
    (qry.LATITUDE, qry.MIN_LATITUDE),
    (qry.LATITUDE, qry.MAX_LATITUDE),
    (qry.LATITUDE, 0),
    (qry.LONGITUDE, qry.MIN_LONGITUDE),
    (qry.LONGITUDE, qry.MAX_LONGITUDE),
    (qry.LONGITUDE, 0),
])
def test_check_valid_state_lat_long_bounds_ok(mock_is_db_up, fld_nm, val):
    assert qry.check_valid_state(**state_args(**{fld_nm: val}))


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm, val', [
    (qry.LATITUDE, qry.MIN_LATITUDE - 0.1),
    (qry.LATITUDE, qry.MAX_LATITUDE + 0.1),
    (qry.LATITUDE, '40'),
    (qry.LATITUDE, None),
    (qry.LATITUDE, True),
    (qry.LONGITUDE, qry.MIN_LONGITUDE - 0.1),
    (qry.LONGITUDE, qry.MAX_LONGITUDE + 0.1),
    (qry.LONGITUDE, '-100'),
    (qry.LONGITUDE, None),
    (qry.LONGITUDE, False),
])
def test_check_valid_state_bad_lat_long(mock_is_db_up, fld_nm, val):
    with pytest.raises(ValueError):
        qry.check_valid_state(**state_args(**{fld_nm: val}))


@pytest.mark.skip(reason="This test is not working right now; fix later!")
def test_that_is_not_working_right_now():
    assert False


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_stores_lat_long(mock_is_db_up, temp_state):
    ret = qry.create(**temp_state)
    assert ret[qry.LATITUDE] == temp_state[qry.LATITUDE]
    assert ret[qry.LONGITUDE] == temp_state[qry.LONGITUDE]


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_bad_lat_long_not_stored(mock_is_db_up, temp_state):
    with pytest.raises(ValueError):
        qry.create(**state_args(**{qry.LATITUDE: 91}))
    assert temp_state[qry.STATE_CODE] not in stored_states()


def test_make_state():
    state = qry.make_state(*[TEST_ST[fld] for fld in (
        qry.STATE_CODE, qry.NAME, qry.POPULATION, qry.CAPITAL, qry.AREA,
        qry.LATITUDE, qry.LONGITUDE)])
    assert state == TEST_ST


def default_state(code, name):
    """
    The state we expect when only the code and name are given.
    """
    return {
        qry.STATE_CODE: code,
        qry.NAME: name,
        qry.POPULATION: 0,
        qry.CAPITAL: '',
        qry.AREA: 0,
        qry.LATITUDE: 0,
        qry.LONGITUDE: 0,
    }


def test_make_state_defaults():
    assert qry.make_state('TS', 'Test State') == default_state('TS',
                                                               'Test State')


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_code_and_name_only(mock_is_db_up, temp_state):
    code = temp_state[qry.STATE_CODE]
    name = temp_state[qry.NAME]
    ret = qry.create(code, name)
    assert ret == default_state(code, name)
    assert stored_states()[code] == ret


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_code_and_name_only(mock_is_db_up, temp_state_in_db):
    code = temp_state_in_db[qry.STATE_CODE]
    ret = qry.update(code, 'New Name')
    assert ret == default_state(code, 'New Name')
    assert stored_states()[code] == ret


@patch('data.db_connect.connect_db', autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_needs_db_connects_when_up(mock_is_db_up, mock_connect):
    @qry.needs_db
    def fn():
        return 'called'
    assert fn() == 'called'
    mock_connect.assert_called_once_with()


@patch('data.db_connect.connect_db', autospec=True)
@patch('states.query.is_db_up', return_value=False, autospec=True)
def test_needs_db_no_connect_when_down(mock_is_db_up, mock_connect):
    @qry.needs_db
    def fn():
        return 'called'
    assert fn() is None
    mock_connect.assert_not_called()


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_read_matches_sample(mock_is_db_up):
    assert qry.read() == SAMPLE_STATES


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_returns_no_mongo_id(mock_is_db_up, temp_state):
    ret = qry.create(**temp_state)
    assert dbc.MONGO_ID not in ret
    assert stored_states()[temp_state[qry.STATE_CODE]] == ret


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_returns_no_mongo_id(mock_is_db_up, temp_state_in_db):
    ret = qry.delete(temp_state_in_db[qry.STATE_CODE])
    assert ret == temp_state_in_db
    assert dbc.MONGO_ID not in ret


@pytest.fixture
def db_down():
    with patch('states.query.is_db_up', return_value=False, autospec=True):
        yield


def test_read_db_down(db_down):
    assert qry.read() is None


def test_exists_db_down(db_down):
    assert qry.exists('AK') is None


@pytest.fixture
def db_call_tracker():
    with patch('states.query.is_db_up',
               return_value=True, autospec=True) as mock_db:
        yield mock_db


def test_read_checks_db(db_call_tracker):
    qry.read()
    db_call_tracker.assert_called_once()


@pytest.fixture
def no_states():
    clear_states()
    yield


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_read_no_states(mock_is_db_up, no_states):
    assert qry.read() == {}


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_into_no_states(mock_is_db_up, no_states):
    qry.create('AL', 'N', 1, 'C', 1.0, 0.0, 0.0)
    assert list(qry.read()) == ['AL']


@pytest.mark.skip(reason="Whitespace-only capitals are not rejected yet.")
def test_check_valid_state_whitespace_capital():
    with pytest.raises(ValueError):
        qry.check_valid_state(TEST_ST[qry.STATE_CODE],
                              TEST_ST[qry.NAME],
                              TEST_ST[qry.POPULATION],
                              ' ',
                              TEST_ST[qry.AREA],
                              TEST_ST[qry.LATITUDE],
                              TEST_ST[qry.LONGITUDE])


@pytest.mark.skip(reason="Tab-only capitals are not rejected yet.")
def test_check_valid_state_tab_capital():
    with pytest.raises(ValueError):
        qry.check_valid_state(TEST_ST[qry.STATE_CODE],
                              TEST_ST[qry.NAME],
                              TEST_ST[qry.POPULATION],
                              '\t',
                              TEST_ST[qry.AREA],
                              TEST_ST[qry.LATITUDE],
                              TEST_ST[qry.LONGITUDE])


@pytest.mark.skip(reason="Lowercase state codes are not rejected yet.")
def test_check_valid_state_lowercase_code():
    with pytest.raises(ValueError):
        qry.check_valid_state('tx',
                              TEST_ST[qry.NAME],
                              TEST_ST[qry.POPULATION],
                              TEST_ST[qry.CAPITAL],
                              TEST_ST[qry.AREA],
                              TEST_ST[qry.LATITUDE],
                              TEST_ST[qry.LONGITUDE])


@pytest.mark.parametrize("invalid_capital", [None, 123, []])
def test_check_valid_state_non_string_capital(
    db_call_tracker, invalid_capital
):
    with pytest.raises(
        ValueError, match="Capital must be a string"
    ):
        qry.check_valid_state(
            TEST_ST[qry.STATE_CODE],
            TEST_ST[qry.NAME],
            TEST_ST[qry.POPULATION],
            invalid_capital,
            TEST_ST[qry.AREA],
            TEST_ST[qry.LATITUDE],
            TEST_ST[qry.LONGITUDE],
        )

    db_call_tracker.assert_called_once()


@pytest.mark.parametrize("invalid_population", [True, False])
def test_check_valid_state_boolean_population(invalid_population):
    with patch("states.query.is_db_up", return_value=True):
        with pytest.raises(ValueError, match="Population must be"):
            qry.check_valid_state(
                TEST_ST[qry.STATE_CODE],
                TEST_ST[qry.NAME],
                invalid_population,
                TEST_ST[qry.CAPITAL],
                TEST_ST[qry.AREA],
                TEST_ST[qry.LATITUDE],
                TEST_ST[qry.LONGITUDE],
            )


@pytest.mark.parametrize("invalid_code", [
    "tx",
    "Tx",
    "T1",
    "A ",
    "1A",
])
def test_check_valid_state_invalid_code_format(invalid_code):
    with patch("states.query.is_db_up", return_value=True):
        with pytest.raises(ValueError, match="uppercase letters"):
            qry.check_valid_state(
                invalid_code,
                TEST_ST[qry.NAME],
                TEST_ST[qry.POPULATION],
                TEST_ST[qry.CAPITAL],
                TEST_ST[qry.AREA],
                TEST_ST[qry.LATITUDE],
                TEST_ST[qry.LONGITUDE],
            )


@pytest.fixture
def known_code():
    return 'AL'


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_exists_true(mock_is_db_up, known_code):
    assert qry.exists(known_code) is True

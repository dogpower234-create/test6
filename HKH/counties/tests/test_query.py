from unittest.mock import patch

import pytest

import counties.query as qry
import states.query as sqry
import data.db_connect as dbc
from counties.sample_data import clear_counties, stored_counties

# counties.query uses needs_db from states.query, so that is where
# is_db_up must be patched.
DB_UP = 'states.query.is_db_up'

TEST_CTY = qry.TEST_COUNTY
TEST_ST_CODE = TEST_CTY[qry.STATE_CODE]
TEST_NAME = TEST_CTY[qry.NAME]


def valid_args(changes=None):
    """
    Return TEST_COUNTY's fields as check_valid_county arguments,
    with any given changes (a dict keyed by field name) applied.
    """
    args = dict(TEST_CTY)
    args.update(changes or {})
    return args


# What create and update store for fields left out:
COUNTY_DEFAULTS = {
    qry.POPULATION: 0,
    qry.AREA: 0,
    qry.METRO_AREA: '',
}


@pytest.fixture
def temp_county():
    yield TEST_CTY
    with patch(DB_UP, return_value=True, autospec=True):
        qry.delete(TEST_ST_CODE, TEST_NAME)


@patch(DB_UP, return_value=True, autospec=True)
def test_read(mock_is_db_up):
    counties = qry.read()
    assert isinstance(counties, dict)
    assert 'Autauga' in counties['AL']


@patch(DB_UP, return_value=True, autospec=True)
def test_exists(mock_is_db_up):
    assert qry.exists('AL', 'Autauga')


@patch(DB_UP, return_value=True, autospec=True)
def test_exists_missing_county(mock_is_db_up):
    assert not qry.exists('AL', 'No Such County')


@patch(DB_UP, return_value=True, autospec=True)
def test_exists_missing_state(mock_is_db_up):
    assert 'ZZ' not in stored_counties()
    assert not qry.exists('ZZ', 'Autauga')


@patch(DB_UP, return_value=True, autospec=True)
def test_read_one(mock_is_db_up):
    assert qry.read_one('AL', 'Autauga') == \
        stored_counties()['AL']['Autauga']


@patch(DB_UP, return_value=True, autospec=True)
def test_read_one_returns_copy(mock_is_db_up):
    """
    Changing the county returned must not change the stored data.
    """
    before = dict(stored_counties()['AL']['Autauga'])
    qry.read_one('AL', 'Autauga')[qry.POPULATION] = -1
    assert stored_counties()['AL']['Autauga'] == before


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('state_code, name', [
    ('AL', 'No Such County'),
    ('ZZ', 'Autauga'),
])
def test_read_one_missing(mock_is_db_up, state_code, name):
    assert qry.read_one(state_code, name) is None


@patch(DB_UP, return_value=True, autospec=True)
def test_has_counties(mock_is_db_up):
    assert qry.has_counties('AL')


@patch(DB_UP, return_value=True, autospec=True)
def test_has_counties_none(mock_is_db_up):
    assert 'AK' not in stored_counties()
    assert not qry.has_counties('AK')


@patch(DB_UP, return_value=True, autospec=True)
def test_has_counties_after_last_deleted(mock_is_db_up):
    qry.create(**valid_args({qry.STATE_CODE: 'AK'}))
    assert qry.has_counties('AK')
    qry.delete('AK', TEST_NAME)
    assert not qry.has_counties('AK')


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county(mock_is_db_up):
    assert qry.check_valid_county(**valid_args())


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_no_metro_area(mock_is_db_up):
    assert qry.check_valid_county(**valid_args({qry.METRO_AREA: ''}))


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_code_and_name_only(mock_is_db_up):
    assert qry.check_valid_county(TEST_ST_CODE, TEST_NAME)


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('field, val', [
    (qry.POPULATION, 0),
    (qry.AREA, 0),
    (qry.METRO_AREA, ''),
])
def test_check_valid_county_default_ok(mock_is_db_up, field, val):
    assert qry.check_valid_county(**valid_args({field: val}))


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_int_area(mock_is_db_up):
    assert qry.check_valid_county(**valid_args({qry.AREA: 600}))


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('field, bad_value', [
    (qry.STATE_CODE, ''),
    (qry.STATE_CODE, 'X' * qry.STATE_CODE_LEN * 2),
    (qry.STATE_CODE, 12),
    (qry.NAME, ''),
    (qry.NAME, None),
    (qry.POPULATION, -1),
    (qry.POPULATION, 1.5),
    (qry.POPULATION, True),
    (qry.AREA, -1.5),
    (qry.AREA, '600'),
    (qry.AREA, True),
    (qry.METRO_AREA, None),
])
def test_check_valid_county_bad_field(mock_is_db_up, field, bad_value):
    with pytest.raises(ValueError):
        qry.check_valid_county(**valid_args({field: bad_value}))


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_state_not_found(mock_is_db_up):
    with pytest.raises(qry.NotFoundError):
        qry.check_valid_county(**valid_args({qry.STATE_CODE: 'ZZ'}))


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_bad_code_before_state_check(mock_is_db_up):
    """
    A malformed state code is bad data (ValueError), not a missing state.
    """
    with pytest.raises(ValueError):
        qry.check_valid_county(**valid_args({qry.STATE_CODE: 'ZZZ'}))


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_lowercase_code(mock_is_db_up):
    """
    Like state codes, county state codes must be uppercase letters:
    a malformed code is bad data (ValueError), not a missing state.
    """
    with pytest.raises(ValueError, match='uppercase letters'):
        qry.check_valid_county(**valid_args({qry.STATE_CODE: 'al'}))


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_blank_name(mock_is_db_up):
    with pytest.raises(ValueError, match='Name must be'):
        qry.check_valid_county(**valid_args({qry.NAME: '   '}))


@patch(DB_UP, return_value=True, autospec=True)
def test_create_blank_name_not_stored(mock_is_db_up):
    before = stored_counties()
    with pytest.raises(ValueError):
        qry.create(**valid_args({qry.NAME: '   '}))
    assert stored_counties() == before


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_dup(mock_is_db_up):
    with pytest.raises(ValueError):
        qry.check_valid_county(**valid_args({qry.NAME: 'Autauga'}))


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_same_name_other_state(mock_is_db_up):
    assert qry.check_valid_county(**valid_args({qry.STATE_CODE: 'AK',
                                                qry.NAME: 'Autauga'}))


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_update_missing(mock_is_db_up):
    with pytest.raises(ValueError):
        qry.check_valid_county(**valid_args(), is_update=True)


@patch(DB_UP, return_value=True, autospec=True)
def test_check_valid_county_update_existing(mock_is_db_up):
    assert qry.check_valid_county(**valid_args({qry.NAME: 'Autauga'}),
                                  is_update=True)


@patch(DB_UP, return_value=True, autospec=True)
def test_create(mock_is_db_up, temp_county):
    ret = qry.create(**temp_county)
    assert ret[qry.POPULATION] == temp_county[qry.POPULATION]
    assert qry.exists(TEST_ST_CODE, TEST_NAME)


@patch(DB_UP, return_value=True, autospec=True)
def test_create_first_county_in_state(mock_is_db_up):
    assert 'AK' not in stored_counties()
    qry.create(**valid_args({qry.STATE_CODE: 'AK'}))
    assert qry.exists('AK', TEST_NAME)
    qry.delete('AK', TEST_NAME)
    assert 'AK' not in stored_counties()


@patch(DB_UP, return_value=True, autospec=True)
def test_create_state_not_found(mock_is_db_up):
    assert not sqry.exists('ZZ')
    before = stored_counties()
    with pytest.raises(qry.NotFoundError):
        qry.create(**valid_args({qry.STATE_CODE: 'ZZ'}))
    assert stored_counties() == before


@patch(DB_UP, return_value=True, autospec=True)
def test_create_dup(mock_is_db_up, temp_county):
    qry.create(**temp_county)
    with pytest.raises(ValueError):
        qry.create(**temp_county)


@patch(DB_UP, return_value=True, autospec=True)
def test_create_invalid(mock_is_db_up):
    before = stored_counties()
    with pytest.raises(ValueError):
        qry.create(**valid_args({qry.POPULATION: -1}))
    assert stored_counties() == before


def test_create_db_down(temp_county):
    with patch(DB_UP, return_value=False, autospec=True):
        assert qry.create(**temp_county) is None
    with patch(DB_UP, return_value=True, autospec=True):
        assert not qry.exists(TEST_ST_CODE, TEST_NAME)


@patch(DB_UP, return_value=True, autospec=True)
def test_update(mock_is_db_up, temp_county):
    qry.create(**temp_county)
    ret = qry.update(TEST_ST_CODE, TEST_NAME, 60000, 700.25, '')
    assert stored_counties()[TEST_ST_CODE][TEST_NAME] == {
        qry.POPULATION: 60000,
        qry.AREA: 700.25,
        qry.METRO_AREA: '',
    }
    assert ret == stored_counties()[TEST_ST_CODE][TEST_NAME]


@patch(DB_UP, return_value=True, autospec=True)
def test_create_code_and_name_only(mock_is_db_up, temp_county):
    ret = qry.create(TEST_ST_CODE, TEST_NAME)
    assert ret == COUNTY_DEFAULTS
    assert stored_counties()[TEST_ST_CODE][TEST_NAME] == COUNTY_DEFAULTS


@patch(DB_UP, return_value=True, autospec=True)
def test_update_code_and_name_only(mock_is_db_up, temp_county):
    qry.create(**temp_county)
    ret = qry.update(TEST_ST_CODE, TEST_NAME)
    assert ret == COUNTY_DEFAULTS
    assert stored_counties()[TEST_ST_CODE][TEST_NAME] == COUNTY_DEFAULTS


@patch(DB_UP, return_value=True, autospec=True)
def test_update_leaves_other_counties(mock_is_db_up, temp_county):
    qry.create(**temp_county)
    others = stored_counties()
    del others[TEST_ST_CODE][TEST_NAME]
    qry.update(TEST_ST_CODE, TEST_NAME, 1, 1.0, 'M')
    for st_code, counties in others.items():
        for name, data in counties.items():
            assert stored_counties()[st_code][name] == data


@patch(DB_UP, return_value=True, autospec=True)
def test_update_missing(mock_is_db_up):
    before = stored_counties()
    with pytest.raises(ValueError):
        qry.update('ZZ', TEST_NAME, 1, 1.0, '')
    assert stored_counties() == before


@patch(DB_UP, return_value=True, autospec=True)
def test_update_invalid_leaves_county_unchanged(mock_is_db_up, temp_county):
    qry.create(**temp_county)
    before = dict(stored_counties()[TEST_ST_CODE][TEST_NAME])
    with pytest.raises(ValueError):
        qry.update(TEST_ST_CODE, TEST_NAME, -1, 1.0, '')
    assert stored_counties()[TEST_ST_CODE][TEST_NAME] == before


@patch(DB_UP, return_value=True, autospec=True)
def test_update_db_down(mock_is_db_up, temp_county):
    qry.create(**temp_county)
    before = dict(stored_counties()[TEST_ST_CODE][TEST_NAME])
    mock_is_db_up.return_value = False
    assert qry.update(TEST_ST_CODE, TEST_NAME, 1, 1.0, '') is None
    assert stored_counties()[TEST_ST_CODE][TEST_NAME] == before


@patch(DB_UP, return_value=True, autospec=True)
def test_delete(mock_is_db_up, temp_county):
    qry.create(**temp_county)
    deleted = qry.delete(TEST_ST_CODE, TEST_NAME)
    assert deleted[qry.POPULATION] == temp_county[qry.POPULATION]
    assert TEST_NAME not in stored_counties()[TEST_ST_CODE]
    assert not qry.exists(TEST_ST_CODE, TEST_NAME)


@patch(DB_UP, return_value=True, autospec=True)
def test_delete_leaves_other_counties(mock_is_db_up, temp_county):
    qry.create(**temp_county)
    others = stored_counties()
    del others[TEST_ST_CODE][TEST_NAME]
    qry.delete(TEST_ST_CODE, TEST_NAME)
    assert stored_counties() == others


@patch(DB_UP, return_value=True, autospec=True)
def test_delete_missing_county(mock_is_db_up):
    before = stored_counties()
    assert qry.delete('AL', 'No Such County') is None
    assert stored_counties() == before


@patch(DB_UP, return_value=True, autospec=True)
def test_delete_missing_state(mock_is_db_up):
    before = stored_counties()
    assert qry.delete('ZZ', TEST_NAME) is None
    assert stored_counties() == before


@pytest.mark.parametrize('fn, args', [
    (qry.read, ()),
    (qry.exists, ('AL', 'Autauga')),
    (qry.read_one, ('AL', 'Autauga')),
    (qry.has_counties, ('AL',)),
    (qry.delete, ('AL', 'Autauga')),
])
def test_db_down_returns_none(fn, args):
    before = stored_counties()
    with patch(DB_UP, return_value=False, autospec=True):
        assert fn(*args) is None
    assert stored_counties() == before


@patch(DB_UP, return_value=True, autospec=True)
def test_main(mock_is_db_up, capsys):
    qry.main()
    out = capsys.readouterr().out
    for state_code, counties in stored_counties().items():
        for name in counties:
            assert f'County: {name}, {state_code}' in out


@patch(DB_UP, return_value=True, autospec=True)
def test_create_stores_doc_in_db(mock_is_db_up, temp_county):
    """
    A county is stored as one document holding its keys and its data.
    """
    qry.create(**temp_county)
    doc = dbc.read_one(qry.COUNTIES_COLLECT,
                       qry.county_filter(TEST_ST_CODE, TEST_NAME))
    del doc[dbc.MONGO_ID]
    assert doc == temp_county


@patch(DB_UP, return_value=True, autospec=True)
def test_read_one_has_no_keys_or_id(mock_is_db_up):
    county = qry.read_one('AL', 'Autauga')
    for fld in (qry.STATE_CODE, qry.NAME, dbc.MONGO_ID):
        assert fld not in county


@patch(DB_UP, return_value=True, autospec=True)
def test_read_after_restart(mock_is_db_up, temp_county):
    """
    Counties live in MongoDB, not in RAM: a new client (as after a
    server restart) still finds a county created before.
    """
    qry.create(**temp_county)
    with patch.object(dbc, 'client', None):
        assert qry.exists(TEST_ST_CODE, TEST_NAME)
        assert qry.read_one(TEST_ST_CODE, TEST_NAME) == \
            qry.county_data(temp_county)


@patch(DB_UP, return_value=True, autospec=True)
def test_read_empty_collection(mock_is_db_up):
    clear_counties()
    assert qry.read() == {}
    assert not qry.has_counties('AL')


def test_county_data():
    doc = {**TEST_CTY, dbc.MONGO_ID: 'some id'}
    assert qry.county_data(doc) == {
        qry.POPULATION: TEST_CTY[qry.POPULATION],
        qry.AREA: TEST_CTY[qry.AREA],
        qry.METRO_AREA: TEST_CTY[qry.METRO_AREA],
    }


def test_main_db_down(capsys):
    with patch(DB_UP, return_value=False, autospec=True):
        qry.main()
    assert 'Database is down.' in capsys.readouterr().out

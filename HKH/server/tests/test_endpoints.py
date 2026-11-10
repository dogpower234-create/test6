from http.client import (
    BAD_REQUEST,
    CONFLICT,
    CREATED,
    FORBIDDEN,
    METHOD_NOT_ALLOWED,
    NOT_ACCEPTABLE,
    NOT_FOUND,
    OK,
    SERVICE_UNAVAILABLE,
    UNAUTHORIZED,
)

from unittest.mock import patch

import pytest

import counties.fields as cflds
import counties.query as cqry
import data.db_connect as dbc
import security.security as sec
import server.endpoints as ep
import states.fields as sflds
import states.query as sqry
from counties.sample_data import stored_counties
from states.sample_data import stored_states

TEST_CLIENT = ep.app.test_client()
TEST_ST = sqry.TEST_STATE

TEST_USER = 'test@example.com'
TEST_AUTH_CODE = 'test-auth-code'
AUTH_HEADERS = {
    ep.USER_ID_HDR: TEST_USER,
    ep.AUTH_CODE_HDR: TEST_AUTH_CODE,
}


def test_hello():
    resp = TEST_CLIENT.get(ep.HELLO_EP)
    resp_json = resp.get_json()
    assert ep.HELLO_RESP in resp_json


def test_hello_response_content():
    resp = TEST_CLIENT.get(ep.HELLO_EP)

    assert resp.status_code == OK
    assert resp.get_json() == {ep.HELLO_RESP: 'world'}


# db_info() calls is_db_up in data.db_connect, so patch it there.
DBC_DB_UP = 'data.db_connect.is_db_up'


@pytest.fixture
def local_db(monkeypatch):
    """
    Use a local MongoDB at the default URI, whatever the environment says.
    """
    monkeypatch.delenv('CLOUD_MONGO', raising=False)
    monkeypatch.delenv(dbc.MONGO_URI_ENV, raising=False)


@patch(DBC_DB_UP, return_value=True, autospec=True)
def test_db_info_up(mock_is_db_up, local_db):
    resp = TEST_CLIENT.get(ep.DB_INFO_EP)
    assert resp.status_code == OK
    assert resp.get_json()[ep.DB_INFO_RESP] == {
        'location': 'local',
        'uri': dbc.DEFAULT_LOCAL_URI,
        'db': dbc.SE_DB,
        'up': True,
    }


@patch(DBC_DB_UP, return_value=False, autospec=True)
def test_db_info_down(mock_is_db_up, local_db):
    resp = TEST_CLIENT.get(ep.DB_INFO_EP)
    assert resp.status_code == SERVICE_UNAVAILABLE
    info = resp.get_json()[ep.DB_INFO_RESP]
    assert info['up'] is False
    assert info['location'] == 'local'


@patch(DBC_DB_UP, return_value=True, autospec=True)
def test_db_info_cloud_hides_password(mock_is_db_up, monkeypatch):
    monkeypatch.setenv('CLOUD_MONGO', dbc.CLOUD)
    monkeypatch.setenv('MONGO_PASSWD', 'not-a-real-password')
    resp = TEST_CLIENT.get(ep.DB_INFO_EP)
    info = resp.get_json()[ep.DB_INFO_RESP]
    assert info['location'] == 'cloud'
    assert info['uri'] is None
    assert 'not-a-real-password' not in resp.get_data(as_text=True)


def test_db_info_endpoint_listed():
    resp = TEST_CLIENT.get(ep.ENDPOINT_EP)
    assert ep.DB_INFO_EP in resp.get_json()[ep.ENDPOINT_RESP]


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_get_states(mock_is_db_up):
    resp = TEST_CLIENT.get(ep.STATES_EP)
    assert resp.status_code == OK
    resp_json = resp.get_json()
    assert ep.STATES_RESP in resp_json
    assert isinstance(resp_json[ep.STATES_RESP], dict)


@patch('states.query.is_db_up', return_value=False, autospec=True)
def test_get_states_db_unavailable(mock_is_db_up):
    resp = TEST_CLIENT.get(ep.STATES_EP)
    assert resp.status_code == SERVICE_UNAVAILABLE


@patch('states.query.is_db_up', return_value=False, autospec=True)
def test_create_db_down(mock_is_db_up):
    ret = sqry.create(TEST_ST[sqry.STATE_CODE],
                      TEST_ST[sqry.NAME],
                      TEST_ST[sqry.POPULATION],
                      TEST_ST[sqry.CAPITAL],
                      TEST_ST[sqry.AREA])
    assert ret is None


@pytest.fixture
def temp_state():
    yield dict(sqry.TEST_STATE)
    with patch('states.query.is_db_up', return_value=True, autospec=True):
        sqry.delete(sqry.TEST_STATE[sqry.STATE_CODE])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state(mock_is_db_up, temp_state):
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state,
                            headers=AUTH_HEADERS)
    assert resp.status_code == CREATED
    assert sqry.exists(temp_state[sqry.STATE_CODE])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_bad_data(mock_is_db_up, temp_state):
    temp_state[sqry.POPULATION] = -1
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state,
                            headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST


# What states.query stores for each optional field left out:
STATE_DEFAULTS = {
    sqry.POPULATION: 0,
    sqry.CAPITAL: '',
    sqry.AREA: 0,
    sqry.LATITUDE: 0,
    sqry.LONGITUDE: 0,
}


def test_optional_flds_all_present():
    assert ep.optional_flds(dict(sqry.TEST_STATE), ep.STATE_OPT_FLDS) == {
        fld: sqry.TEST_STATE[fld] for fld in ep.STATE_OPT_FLDS}


def test_optional_flds_none_present():
    assert ep.optional_flds({sqry.STATE_CODE: 'TS',
                             sqry.NAME: 'Test State'},
                            ep.STATE_OPT_FLDS) == {}


def test_optional_flds_keeps_explicit_none():
    """
    A field sent as null is passed on, so validation can reject it.
    """
    assert ep.optional_flds({sqry.AREA: None}, ep.STATE_OPT_FLDS) == {
        sqry.AREA: None}


def test_optional_flds_ignores_other_keys():
    assert ep.optional_flds({'bogus': 1, sqry.AREA: 5},
                            ep.STATE_OPT_FLDS) == {sqry.AREA: 5}


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm', ep.STATE_OPT_FLDS)
def test_create_state_missing_optional(mock_is_db_up, fld_nm, temp_state):
    del temp_state[fld_nm]
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state,
                            headers=AUTH_HEADERS)
    assert resp.status_code == CREATED
    stored = stored_states()[temp_state[sqry.STATE_CODE]]
    assert stored == {**temp_state, fld_nm: STATE_DEFAULTS[fld_nm]}


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_code_and_name_only(mock_is_db_up, temp_state):
    code = temp_state[sqry.STATE_CODE]
    body = {sqry.STATE_CODE: code, sqry.NAME: temp_state[sqry.NAME]}
    resp = TEST_CLIENT.post(ep.STATES_EP, json=body, headers=AUTH_HEADERS)
    assert resp.status_code == CREATED
    assert stored_states()[code] == {**body, **STATE_DEFAULTS}
    assert resp.get_json()[ep.STATES_RESP] == stored_states()[code]


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm', [sqry.STATE_CODE, sqry.NAME])
def test_create_state_missing_required(mock_is_db_up, fld_nm, temp_state):
    code = temp_state[sqry.STATE_CODE]
    del temp_state[fld_nm]
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state,
                            headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert not sqry.exists(code)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_null_optional(mock_is_db_up, temp_state):
    temp_state[sqry.AREA] = None
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state,
                            headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert not sqry.exists(temp_state[sqry.STATE_CODE])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_stores_lat_long(mock_is_db_up, temp_state):
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state,
                            headers=AUTH_HEADERS)
    stored = resp.get_json()[ep.STATES_RESP]
    assert stored[sqry.LATITUDE] == temp_state[sqry.LATITUDE]
    assert stored[sqry.LONGITUDE] == temp_state[sqry.LONGITUDE]


@patch('states.query.is_db_up', return_value=False, autospec=True)
def test_create_state_db_unavailable(mock_is_db_up, temp_state):
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state,
                            headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('missing', [ep.USER_ID_HDR, ep.AUTH_CODE_HDR])
def test_create_state_missing_auth_header(mock_is_db_up, missing,
                                          temp_state):
    headers = {k: v for k, v in AUTH_HEADERS.items() if k != missing}
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state, headers=headers)
    assert resp.status_code == UNAUTHORIZED
    assert not sqry.exists(temp_state[sqry.STATE_CODE])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_empty_auth_header(mock_is_db_up, temp_state):
    headers = dict(AUTH_HEADERS)
    headers[ep.AUTH_CODE_HDR] = ''
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state, headers=headers)
    assert resp.status_code == UNAUTHORIZED
    assert not sqry.exists(temp_state[sqry.STATE_CODE])


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_creds_not_in_body(mock_is_db_up, temp_state):
    """
    Credentials must come in the headers; putting them in the body
    does not count.
    """
    body = dict(temp_state)
    body[ep.USER_ID_HDR] = TEST_USER
    body[ep.AUTH_CODE_HDR] = TEST_AUTH_CODE
    resp = TEST_CLIENT.post(ep.STATES_EP, json=body)
    assert resp.status_code == UNAUTHORIZED
    assert not sqry.exists(temp_state[sqry.STATE_CODE])


@patch('security.security.is_permitted', return_value=False, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_not_permitted(mock_is_db_up, mock_is_permitted,
                                    temp_state):
    resp = TEST_CLIENT.post(ep.STATES_EP, json=temp_state,
                            headers=AUTH_HEADERS)
    assert resp.status_code == FORBIDDEN
    assert not sqry.exists(temp_state[sqry.STATE_CODE])


@patch('security.security.is_permitted', return_value=True, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_checks_permission(mock_is_db_up, mock_is_permitted,
                                        temp_state):
    TEST_CLIENT.post(ep.STATES_EP, json=temp_state, headers=AUTH_HEADERS)
    mock_is_permitted.assert_called_once_with(sec.STATES, sec.CREATE,
                                              TEST_USER,
                                              auth_code=TEST_AUTH_CODE)


@pytest.fixture
def existing_state(temp_state):
    with patch('states.query.is_db_up', return_value=True, autospec=True):
        sqry.create(**temp_state)
    return temp_state


def state_url(state_code):
    return f'{ep.STATES_EP}/{state_code}'


def updated_fields():
    return {
        sqry.POPULATION: 2000000,
        sqry.CAPITAL: 'New Capital',
        sqry.AREA: 60000.5,
        sqry.NAME: 'New Name',
        sqry.LATITUDE: 33.5,
        sqry.LONGITUDE: -87.5,
    }


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    resp = TEST_CLIENT.put(state_url(code), json=updated_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == OK
    expected = {**updated_fields(), sqry.STATE_CODE: code}
    assert stored_states()[code] == expected
    assert resp.get_json()[ep.STATES_RESP] == expected


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_matching_code_in_body(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    body = updated_fields()
    body[sqry.STATE_CODE] = code
    resp = TEST_CLIENT.put(state_url(code), json=body, headers=AUTH_HEADERS)
    assert resp.status_code == OK
    assert stored_states()[code] == {**updated_fields(),
                                     sqry.STATE_CODE: code}


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_cannot_change_code(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    before = dict(stored_states()[code])
    body = updated_fields()
    body[sqry.STATE_CODE] = 'ZZ'
    resp = TEST_CLIENT.put(state_url(code), json=body, headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_states()[code] == before
    assert not sqry.exists('ZZ')


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_not_found(mock_is_db_up, temp_state):
    code = temp_state[sqry.STATE_CODE]
    resp = TEST_CLIENT.put(state_url(code), json=updated_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == NOT_FOUND
    assert not sqry.exists(code)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_bad_data(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    before = dict(stored_states()[code])
    body = updated_fields()
    body[sqry.POPULATION] = -1
    resp = TEST_CLIENT.put(state_url(code), json=body, headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_states()[code] == before


def test_update_args_all_sent():
    assert ep.update_args(sqry.TEST_STATE, updated_fields(),
                          ep.STATE_UPD_FLDS) == updated_fields()


def test_update_args_none_sent():
    expected = {k: v for k, v in sqry.TEST_STATE.items()
                if k != sqry.STATE_CODE}
    assert ep.update_args(sqry.TEST_STATE, {}, ep.STATE_UPD_FLDS) \
        == expected


def test_update_args_some_sent():
    args = ep.update_args(sqry.TEST_STATE, {sqry.AREA: 7},
                          ep.STATE_UPD_FLDS)
    assert args[sqry.AREA] == 7
    assert args[sqry.NAME] == sqry.TEST_STATE[sqry.NAME]
    assert args[sqry.CAPITAL] == sqry.TEST_STATE[sqry.CAPITAL]


def test_update_args_ignores_other_keys():
    args = ep.update_args(sqry.TEST_STATE,
                          {sqry.STATE_CODE: 'ZZ', 'bogus': 1},
                          ep.STATE_UPD_FLDS)
    assert sqry.STATE_CODE not in args
    assert 'bogus' not in args


def test_update_args_field_missing_from_current():
    """
    A field neither stored nor sent is left out, so it gets its default.
    """
    current = {sqry.STATE_CODE: 'TS', sqry.NAME: 'Test State'}
    assert ep.update_args(current, {}, ep.STATE_UPD_FLDS) == {
        sqry.NAME: 'Test State'}


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm', ep.STATE_UPD_FLDS)
def test_update_state_one_field(mock_is_db_up, fld_nm, existing_state):
    code = existing_state[sqry.STATE_CODE]
    new_val = updated_fields()[fld_nm]
    resp = TEST_CLIENT.put(state_url(code), json={fld_nm: new_val},
                           headers=AUTH_HEADERS)
    assert resp.status_code == OK
    expected = {**existing_state, fld_nm: new_val}
    assert stored_states()[code] == expected
    assert resp.get_json()[ep.STATES_RESP] == expected


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_empty_body(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    resp = TEST_CLIENT.put(state_url(code), json={}, headers=AUTH_HEADERS)
    assert resp.status_code == OK
    assert stored_states()[code] == existing_state


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_null_field(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    resp = TEST_CLIENT.put(state_url(code), json={sqry.CAPITAL: None},
                           headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_states()[code] == existing_state


@patch('states.query.read_one', return_value=None, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_db_down_during_read(mock_is_db_up, mock_read_one,
                                          existing_state):
    code = existing_state[sqry.STATE_CODE]
    resp = TEST_CLIENT.put(state_url(code), json=updated_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE
    assert stored_states()[code] == existing_state


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_bad_longitude(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    before = dict(stored_states()[code])
    body = updated_fields()
    body[sqry.LONGITUDE] = 181
    resp = TEST_CLIENT.put(state_url(code), json=body, headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_states()[code] == before


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_db_unavailable(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    before = dict(stored_states()[code])
    mock_is_db_up.return_value = False
    resp = TEST_CLIENT.put(state_url(code), json=updated_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE
    assert stored_states()[code] == before


@patch('states.query.update', return_value=None, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_db_down_during_update(mock_is_db_up, mock_update,
                                            existing_state):
    resp = TEST_CLIENT.put(state_url(existing_state[sqry.STATE_CODE]),
                           json=updated_fields(), headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('missing', [ep.USER_ID_HDR, ep.AUTH_CODE_HDR])
def test_update_state_missing_auth_header(mock_is_db_up, missing,
                                          existing_state):
    code = existing_state[sqry.STATE_CODE]
    before = dict(stored_states()[code])
    headers = {k: v for k, v in AUTH_HEADERS.items() if k != missing}
    resp = TEST_CLIENT.put(state_url(code), json=updated_fields(),
                           headers=headers)
    assert resp.status_code == UNAUTHORIZED
    assert stored_states()[code] == before


@patch('security.security.is_permitted', return_value=False, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_not_permitted(mock_is_db_up, mock_is_permitted,
                                    existing_state):
    code = existing_state[sqry.STATE_CODE]
    before = dict(stored_states()[code])
    resp = TEST_CLIENT.put(state_url(code), json=updated_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == FORBIDDEN
    assert stored_states()[code] == before


@patch('security.security.is_permitted', return_value=True, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_checks_permission(mock_is_db_up, mock_is_permitted,
                                        existing_state):
    TEST_CLIENT.put(state_url(existing_state[sqry.STATE_CODE]),
                    json=updated_fields(), headers=AUTH_HEADERS)
    mock_is_permitted.assert_called_once_with(sec.STATES, sec.UPDATE,
                                              TEST_USER,
                                              auth_code=TEST_AUTH_CODE)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_put_on_states_collection_not_allowed(mock_is_db_up, existing_state):
    resp = TEST_CLIENT.put(ep.STATES_EP, json=existing_state,
                           headers=AUTH_HEADERS)
    assert resp.status_code == METHOD_NOT_ALLOWED


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    expected = dict(stored_states()[code])
    resp = TEST_CLIENT.delete(state_url(code), headers=AUTH_HEADERS)
    assert resp.status_code == OK
    assert resp.get_json()[ep.STATES_RESP] == expected
    assert code not in stored_states()


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_leaves_other_states(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    others = {k: dict(v) for k, v in stored_states().items()
              if k != code}
    TEST_CLIENT.delete(state_url(code), headers=AUTH_HEADERS)
    assert stored_states() == others


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_with_counties(mock_is_db_up):
    assert cqry.has_counties('AL')
    before = dict(stored_states()['AL'])
    resp = TEST_CLIENT.delete(state_url('AL'), headers=AUTH_HEADERS)
    assert resp.status_code == CONFLICT
    assert stored_states()['AL'] == before


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_not_found(mock_is_db_up):
    assert 'ZZ' not in stored_states()
    resp = TEST_CLIENT.delete(state_url('ZZ'), headers=AUTH_HEADERS)
    assert resp.status_code == NOT_FOUND


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_db_unavailable(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    mock_is_db_up.return_value = False
    resp = TEST_CLIENT.delete(state_url(code), headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE
    assert code in stored_states()


@patch('states.query.delete', return_value=None, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_db_down_during_delete(mock_is_db_up, mock_delete,
                                            existing_state):
    resp = TEST_CLIENT.delete(state_url(existing_state[sqry.STATE_CODE]),
                              headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('missing', [ep.USER_ID_HDR, ep.AUTH_CODE_HDR])
def test_delete_state_missing_auth_header(mock_is_db_up, missing,
                                          existing_state):
    code = existing_state[sqry.STATE_CODE]
    headers = {k: v for k, v in AUTH_HEADERS.items() if k != missing}
    resp = TEST_CLIENT.delete(state_url(code), headers=headers)
    assert resp.status_code == UNAUTHORIZED
    assert code in stored_states()


@patch('security.security.is_permitted', return_value=False, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_not_permitted(mock_is_db_up, mock_is_permitted,
                                    existing_state):
    code = existing_state[sqry.STATE_CODE]
    resp = TEST_CLIENT.delete(state_url(code), headers=AUTH_HEADERS)
    assert resp.status_code == FORBIDDEN
    assert code in stored_states()


@patch('security.security.is_permitted', return_value=True, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_checks_permission(mock_is_db_up, mock_is_permitted,
                                        existing_state):
    TEST_CLIENT.delete(state_url(existing_state[sqry.STATE_CODE]),
                       headers=AUTH_HEADERS)
    mock_is_permitted.assert_called_once_with(sec.STATES, sec.DELETE,
                                              TEST_USER,
                                              auth_code=TEST_AUTH_CODE)


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_on_states_collection_not_allowed(mock_is_db_up,
                                                 existing_state):
    resp = TEST_CLIENT.delete(ep.STATES_EP, headers=AUTH_HEADERS)
    assert resp.status_code == METHOD_NOT_ALLOWED
    assert existing_state[sqry.STATE_CODE] in stored_states()


def test_get_state_fields():
    resp = TEST_CLIENT.get(ep.STATE_FLDS_EP)
    assert resp.status_code == OK
    assert resp.get_json()[ep.STATE_FLDS_RESP] == sflds.get_flds()


def test_get_state_fields_describes_every_field():
    resp = TEST_CLIENT.get(ep.STATE_FLDS_EP)
    state_flds = resp.get_json()[ep.STATE_FLDS_RESP]
    assert set(state_flds) == set(sqry.TEST_STATE)
    for fld in state_flds.values():
        assert sflds.DISP_NAME in fld
        assert sflds.FLD_TYPE in fld


@patch('states.query.is_db_up', return_value=False, autospec=True)
def test_get_state_fields_db_down(mock_is_db_up):
    """
    The data dictionary is static, so it is served even if the DB is down.
    """
    resp = TEST_CLIENT.get(ep.STATE_FLDS_EP)
    assert resp.status_code == OK


def test_get_state_fields_no_auth_needed():
    resp = TEST_CLIENT.get(ep.STATE_FLDS_EP)
    assert resp.status_code == OK


@patch('states.query.is_db_up', return_value=True, autospec=True)
@pytest.mark.parametrize('method', ['post', 'put', 'delete'])
def test_state_fields_read_only(mock_is_db_up, method):
    """
    /states/fields only allows GET. PUT and DELETE fall through to
    /states/<state_code>, where they are rejected because no state has
    the code 'fields'.
    """
    before = dict(stored_states())
    resp = getattr(TEST_CLIENT, method)(ep.STATE_FLDS_EP,
                                        json=sqry.TEST_STATE,
                                        headers=AUTH_HEADERS)
    assert resp.status_code >= BAD_REQUEST
    assert stored_states() == before


def test_state_fields_endpoint_listed():
    resp = TEST_CLIENT.get(ep.ENDPOINT_EP)
    endpoints = resp.get_json()[ep.ENDPOINT_RESP]
    assert ep.STATE_FLDS_EP in endpoints


# counties.query uses needs_db from states.query, so that is where
# is_db_up must be patched for county endpoints too.
DB_UP = 'states.query.is_db_up'

TEST_CTY = cqry.TEST_COUNTY
CTY_ST_CODE = TEST_CTY[cqry.STATE_CODE]
CTY_NAME = TEST_CTY[cqry.NAME]


def county_url(state_code, name):
    return f'{ep.COUNTIES_EP}/{state_code}/{name}'


def stored_county(state_code=CTY_ST_CODE, name=CTY_NAME):
    return stored_counties()[state_code][name]


def county_exists(state_code=CTY_ST_CODE, name=CTY_NAME):
    return name in stored_counties().get(state_code, {})


def updated_county_fields():
    return {
        cqry.POPULATION: 60000,
        cqry.AREA: 700.25,
        cqry.METRO_AREA: '',
    }


# What counties.query stores for each optional field left out:
COUNTY_DEFAULTS = {
    cqry.POPULATION: 0,
    cqry.AREA: 0,
    cqry.METRO_AREA: '',
}


@pytest.fixture
def temp_county():
    yield dict(TEST_CTY)
    with patch(DB_UP, return_value=True, autospec=True):
        cqry.delete(CTY_ST_CODE, CTY_NAME)


@pytest.fixture
def existing_county(temp_county):
    with patch(DB_UP, return_value=True, autospec=True):
        cqry.create(**temp_county)
    return temp_county


@patch(DB_UP, return_value=True, autospec=True)
def test_get_counties(mock_is_db_up):
    resp = TEST_CLIENT.get(ep.COUNTIES_EP)
    assert resp.status_code == OK
    counties = resp.get_json()[ep.COUNTIES_RESP]
    assert counties == stored_counties()


@patch(DB_UP, return_value=False, autospec=True)
def test_get_counties_db_unavailable(mock_is_db_up):
    resp = TEST_CLIENT.get(ep.COUNTIES_EP)
    assert resp.status_code == SERVICE_UNAVAILABLE


@patch(DB_UP, return_value=True, autospec=True)
def test_create_county(mock_is_db_up, temp_county):
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == CREATED
    assert county_exists()
    assert resp.get_json()[ep.COUNTIES_RESP] == stored_county()


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm', ep.COUNTY_OPT_FLDS)
def test_create_county_missing_optional(mock_is_db_up, fld_nm, temp_county):
    del temp_county[fld_nm]
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == CREATED
    expected = {fld: temp_county.get(fld, COUNTY_DEFAULTS[fld])
                for fld in ep.COUNTY_OPT_FLDS}
    assert stored_county() == expected


@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_code_and_name_only(mock_is_db_up, temp_county):
    body = {cqry.STATE_CODE: CTY_ST_CODE, cqry.NAME: CTY_NAME}
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=body, headers=AUTH_HEADERS)
    assert resp.status_code == CREATED
    assert stored_county() == COUNTY_DEFAULTS
    assert resp.get_json()[ep.COUNTIES_RESP] == COUNTY_DEFAULTS


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm', [cqry.STATE_CODE, cqry.NAME])
def test_create_county_missing_required(mock_is_db_up, fld_nm, temp_county):
    del temp_county[fld_nm]
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert not county_exists()


@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_null_optional(mock_is_db_up, temp_county):
    temp_county[cqry.AREA] = None
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert not county_exists()


@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_bad_data(mock_is_db_up, temp_county):
    temp_county[cqry.POPULATION] = -1
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert not county_exists()


@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_state_not_found(mock_is_db_up, temp_county):
    temp_county[cqry.STATE_CODE] = 'ZZ'
    assert not sqry.exists('ZZ')
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == NOT_FOUND
    assert not county_exists('ZZ')


@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_dup(mock_is_db_up, existing_county):
    before = dict(stored_county())
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=existing_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_county() == before


@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_no_body(mock_is_db_up):
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST


@patch(DB_UP, return_value=False, autospec=True)
def test_create_county_db_unavailable(mock_is_db_up, temp_county):
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE
    assert not county_exists()


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('missing', [ep.USER_ID_HDR, ep.AUTH_CODE_HDR])
def test_create_county_missing_auth_header(mock_is_db_up, missing,
                                           temp_county):
    headers = {k: v for k, v in AUTH_HEADERS.items() if k != missing}
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=headers)
    assert resp.status_code == UNAUTHORIZED
    assert not county_exists()


@patch('security.security.is_permitted', return_value=False, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_not_permitted(mock_is_db_up, mock_is_permitted,
                                     temp_county):
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county,
                            headers=AUTH_HEADERS)
    assert resp.status_code == FORBIDDEN
    assert not county_exists()


@patch('security.security.is_permitted', return_value=True, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_checks_permission(mock_is_db_up, mock_is_permitted,
                                         temp_county):
    TEST_CLIENT.post(ep.COUNTIES_EP, json=temp_county, headers=AUTH_HEADERS)
    mock_is_permitted.assert_called_once_with(sec.COUNTIES, sec.CREATE,
                                              TEST_USER,
                                              auth_code=TEST_AUTH_CODE)


@patch(DB_UP, return_value=True, autospec=True)
def test_update_county(mock_is_db_up, existing_county):
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json=updated_county_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == OK
    assert stored_county() == updated_county_fields()
    assert resp.get_json()[ep.COUNTIES_RESP] == updated_county_fields()


def existing_county_flds(county):
    """
    The stored fields of a county created from the given record.
    """
    return {fld: county[fld] for fld in ep.COUNTY_OPT_FLDS}


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('fld_nm', ep.COUNTY_OPT_FLDS)
def test_update_county_one_field(mock_is_db_up, fld_nm, existing_county):
    new_val = updated_county_fields()[fld_nm]
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json={fld_nm: new_val}, headers=AUTH_HEADERS)
    assert resp.status_code == OK
    expected = {**existing_county_flds(existing_county), fld_nm: new_val}
    assert stored_county() == expected
    assert resp.get_json()[ep.COUNTIES_RESP] == expected


@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_empty_body(mock_is_db_up, existing_county):
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME), json={},
                           headers=AUTH_HEADERS)
    assert resp.status_code == OK
    assert stored_county() == existing_county_flds(existing_county)


@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_null_field(mock_is_db_up, existing_county):
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json={cqry.METRO_AREA: None},
                           headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_county() == existing_county_flds(existing_county)


@patch('counties.query.read_one', return_value=None, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_db_down_during_read(mock_is_db_up, mock_read_one,
                                           existing_county):
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json=updated_county_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE
    assert stored_county() == existing_county_flds(existing_county)


@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_matching_ids_in_body(mock_is_db_up, existing_county):
    body = updated_county_fields()
    body[cqry.STATE_CODE] = CTY_ST_CODE
    body[cqry.NAME] = CTY_NAME
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME), json=body,
                           headers=AUTH_HEADERS)
    assert resp.status_code == OK
    assert stored_county() == updated_county_fields()


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('field, new_value', [
    (cqry.STATE_CODE, 'ZZ'),
    (cqry.NAME, 'Other County'),
])
def test_update_county_cannot_change_ids(mock_is_db_up, field, new_value,
                                         existing_county):
    before = dict(stored_county())
    body = updated_county_fields()
    body[field] = new_value
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME), json=body,
                           headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_county() == before


@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_not_found(mock_is_db_up, temp_county):
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json=updated_county_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == NOT_FOUND
    assert not county_exists()


@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_wrong_state(mock_is_db_up, existing_county):
    """
    A county is found by state code and name together.
    """
    resp = TEST_CLIENT.put(county_url('AK', CTY_NAME),
                           json=updated_county_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == NOT_FOUND
    assert not county_exists('AK')


@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_bad_data(mock_is_db_up, existing_county):
    before = dict(stored_county())
    body = updated_county_fields()
    body[cqry.POPULATION] = -1
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME), json=body,
                           headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_county() == before


@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_db_unavailable(mock_is_db_up, existing_county):
    before = dict(stored_county())
    mock_is_db_up.return_value = False
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json=updated_county_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE
    assert stored_county() == before


@patch('counties.query.update', return_value=None, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_db_down_during_update(mock_is_db_up, mock_update,
                                             existing_county):
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json=updated_county_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('missing', [ep.USER_ID_HDR, ep.AUTH_CODE_HDR])
def test_update_county_missing_auth_header(mock_is_db_up, missing,
                                           existing_county):
    before = dict(stored_county())
    headers = {k: v for k, v in AUTH_HEADERS.items() if k != missing}
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json=updated_county_fields(), headers=headers)
    assert resp.status_code == UNAUTHORIZED
    assert stored_county() == before


@patch('security.security.is_permitted', return_value=False, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_not_permitted(mock_is_db_up, mock_is_permitted,
                                     existing_county):
    before = dict(stored_county())
    resp = TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                           json=updated_county_fields(),
                           headers=AUTH_HEADERS)
    assert resp.status_code == FORBIDDEN
    assert stored_county() == before


@patch('security.security.is_permitted', return_value=True, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_update_county_checks_permission(mock_is_db_up, mock_is_permitted,
                                         existing_county):
    TEST_CLIENT.put(county_url(CTY_ST_CODE, CTY_NAME),
                    json=updated_county_fields(), headers=AUTH_HEADERS)
    mock_is_permitted.assert_called_once_with(sec.COUNTIES, sec.UPDATE,
                                              TEST_USER,
                                              auth_code=TEST_AUTH_CODE)


@patch(DB_UP, return_value=True, autospec=True)
def test_put_on_counties_collection_not_allowed(mock_is_db_up,
                                                existing_county):
    resp = TEST_CLIENT.put(ep.COUNTIES_EP, json=existing_county,
                           headers=AUTH_HEADERS)
    assert resp.status_code == METHOD_NOT_ALLOWED


@patch(DB_UP, return_value=True, autospec=True)
def test_delete_county(mock_is_db_up, existing_county):
    expected = dict(stored_county())
    resp = TEST_CLIENT.delete(county_url(CTY_ST_CODE, CTY_NAME),
                              headers=AUTH_HEADERS)
    assert resp.status_code == OK
    assert resp.get_json()[ep.COUNTIES_RESP] == expected
    assert not county_exists()


@patch(DB_UP, return_value=True, autospec=True)
def test_delete_county_leaves_other_counties(mock_is_db_up, existing_county):
    others = {st: {nm: dict(d) for nm, d in cties.items()
                   if (st, nm) != (CTY_ST_CODE, CTY_NAME)}
              for st, cties in stored_counties().items()}
    TEST_CLIENT.delete(county_url(CTY_ST_CODE, CTY_NAME),
                       headers=AUTH_HEADERS)
    assert stored_counties() == others


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('state_code, name', [
    ('AL', 'No Such County'),
    ('ZZ', 'Autauga'),
])
def test_delete_county_not_found(mock_is_db_up, state_code, name):
    resp = TEST_CLIENT.delete(county_url(state_code, name),
                              headers=AUTH_HEADERS)
    assert resp.status_code == NOT_FOUND


@patch(DB_UP, return_value=True, autospec=True)
def test_delete_county_db_unavailable(mock_is_db_up, existing_county):
    mock_is_db_up.return_value = False
    resp = TEST_CLIENT.delete(county_url(CTY_ST_CODE, CTY_NAME),
                              headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE
    assert county_exists()


@patch('counties.query.delete', return_value=None, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_delete_county_db_down_during_delete(mock_is_db_up, mock_delete,
                                             existing_county):
    resp = TEST_CLIENT.delete(county_url(CTY_ST_CODE, CTY_NAME),
                              headers=AUTH_HEADERS)
    assert resp.status_code == SERVICE_UNAVAILABLE


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('missing', [ep.USER_ID_HDR, ep.AUTH_CODE_HDR])
def test_delete_county_missing_auth_header(mock_is_db_up, missing,
                                           existing_county):
    headers = {k: v for k, v in AUTH_HEADERS.items() if k != missing}
    resp = TEST_CLIENT.delete(county_url(CTY_ST_CODE, CTY_NAME),
                              headers=headers)
    assert resp.status_code == UNAUTHORIZED
    assert county_exists()


@patch('security.security.is_permitted', return_value=False, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_delete_county_not_permitted(mock_is_db_up, mock_is_permitted,
                                     existing_county):
    resp = TEST_CLIENT.delete(county_url(CTY_ST_CODE, CTY_NAME),
                              headers=AUTH_HEADERS)
    assert resp.status_code == FORBIDDEN
    assert county_exists()


@patch('security.security.is_permitted', return_value=True, autospec=True)
@patch(DB_UP, return_value=True, autospec=True)
def test_delete_county_checks_permission(mock_is_db_up, mock_is_permitted,
                                         existing_county):
    TEST_CLIENT.delete(county_url(CTY_ST_CODE, CTY_NAME),
                       headers=AUTH_HEADERS)
    mock_is_permitted.assert_called_once_with(sec.COUNTIES, sec.DELETE,
                                              TEST_USER,
                                              auth_code=TEST_AUTH_CODE)


@patch(DB_UP, return_value=True, autospec=True)
def test_delete_on_counties_collection_not_allowed(mock_is_db_up,
                                                   existing_county):
    resp = TEST_CLIENT.delete(ep.COUNTIES_EP, headers=AUTH_HEADERS)
    assert resp.status_code == METHOD_NOT_ALLOWED
    assert county_exists()


def test_county_endpoints_listed():
    resp = TEST_CLIENT.get(ep.ENDPOINT_EP)
    endpoints = resp.get_json()[ep.ENDPOINT_RESP]
    assert ep.COUNTIES_EP in endpoints
    assert ep.COUNTY_EP in endpoints
    assert ep.COUNTY_FLDS_EP in endpoints


def test_get_county_fields():
    resp = TEST_CLIENT.get(ep.COUNTY_FLDS_EP)
    assert resp.status_code == OK
    assert resp.get_json()[ep.COUNTY_FLDS_RESP] == cflds.get_flds()


def test_get_county_fields_describes_every_field():
    resp = TEST_CLIENT.get(ep.COUNTY_FLDS_EP)
    county_flds = resp.get_json()[ep.COUNTY_FLDS_RESP]
    assert set(county_flds) == set(cqry.TEST_COUNTY)
    for fld in county_flds.values():
        assert cflds.DISP_NAME in fld
        assert cflds.FLD_TYPE in fld


@patch(DB_UP, return_value=False, autospec=True)
def test_get_county_fields_db_down(mock_is_db_up):
    """
    The data dictionary is static, so it is served even if the DB is down.
    """
    resp = TEST_CLIENT.get(ep.COUNTY_FLDS_EP)
    assert resp.status_code == OK


def test_get_county_fields_no_auth_needed():
    resp = TEST_CLIENT.get(ep.COUNTY_FLDS_EP)
    assert resp.status_code == OK


@patch(DB_UP, return_value=True, autospec=True)
@pytest.mark.parametrize('method', ['post', 'put', 'delete'])
def test_county_fields_read_only(mock_is_db_up, method):
    """
    /counties/fields only allows GET. Unlike /states/fields, no other
    route matches it: a single county needs both a state code and a name.
    """
    before = stored_counties()
    resp = getattr(TEST_CLIENT, method)(ep.COUNTY_FLDS_EP,
                                        json=TEST_CTY,
                                        headers=AUTH_HEADERS)
    assert resp.status_code == METHOD_NOT_ALLOWED
    assert stored_counties() == before


def test_get_endpoints():
    resp = TEST_CLIENT.get(ep.ENDPOINT_EP)

    assert resp.status_code == OK

    resp_json = resp.get_json()
    assert ep.ENDPOINT_RESP in resp_json

    endpoints = resp_json[ep.ENDPOINT_RESP]
    assert isinstance(endpoints, list)

    expected_routes = {ep.HELLO_EP, ep.ENDPOINT_EP, ep.STATES_EP}
    assert expected_routes.issubset(set(endpoints))

    assert endpoints == sorted(endpoints)


@patch('server.endpoints.sqry.read', return_value={}, autospec=True)
def test_get_states_empty_result(mock_read):
    resp = TEST_CLIENT.get(ep.STATES_EP)

    assert resp.status_code == OK
    assert resp.get_json() == {ep.STATES_RESP: {}}
    mock_read.assert_called_once_with()


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_empty_auth_header(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    headers = dict(AUTH_HEADERS)
    headers[ep.AUTH_CODE_HDR] = ''
    resp = TEST_CLIENT.put(state_url(code), json=updated_fields(),
                           headers=headers)
    assert resp.status_code == UNAUTHORIZED


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_empty_auth_header(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    headers = dict(AUTH_HEADERS)
    headers[ep.AUTH_CODE_HDR] = ''
    resp = TEST_CLIENT.delete(state_url(code), headers=headers)
    assert resp.status_code == UNAUTHORIZED


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_not_found_keeps_data(mock_is_db_up, existing_state):
    assert not sqry.exists('ZZ')
    before = {k: dict(v) for k, v in sqry.read().items()}
    TEST_CLIENT.delete(state_url('ZZ'), headers=AUTH_HEADERS)
    assert sqry.read() == before


@patch('security.security.is_permitted', return_value=False, autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_delete_state_not_permitted_keeps_data(mock_is_db_up,
                                               mock_is_permitted,
                                               existing_state):
    code = existing_state[sqry.STATE_CODE]
    before = {k: dict(v) for k, v in sqry.read().items()}
    TEST_CLIENT.delete(state_url(code), headers=AUTH_HEADERS)
    assert sqry.read() == before


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_get_state_detail_success(mock_is_db_up):
    resp = TEST_CLIENT.get(state_url('AL'))

    assert resp.status_code == OK
    assert resp.get_json() == {
        ep.STATES_RESP: {
            'AL': stored_states()['AL']
        }
    }


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_get_state_detail_not_found(mock_is_db_up):
    resp = TEST_CLIENT.get(state_url('ZZ'))

    assert resp.status_code == NOT_FOUND


@patch('states.query.is_db_up', return_value=False, autospec=True)
def test_get_state_detail_db_unavailable(mock_is_db_up):
    resp = TEST_CLIENT.get(state_url('AL'))
    assert resp.status_code == SERVICE_UNAVAILABLE


@patch('server.endpoints.sqry.read', autospec=True)
@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_get_state_detail_reads_one_state(mock_is_db_up, mock_read):
    """
    Getting one state should not read every state from the DB.
    """
    resp = TEST_CLIENT.get(state_url('AL'))
    assert resp.status_code == OK
    mock_read.assert_not_called()


def test_state_route_listed_once():
    """
    GET, PUT and DELETE on a single state share one route, so
    /endpoints lists /states/<state_code> once, with no duplicate.
    """
    resp = TEST_CLIENT.get(ep.ENDPOINT_EP)
    endpoints = resp.get_json()[ep.ENDPOINT_RESP]
    state_routes = [route for route in endpoints
                    if route.startswith(f'{ep.STATES_EP}/<')]
    assert state_routes == [ep.STATE_EP]


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_create_state_list_body(mock_is_db_up):
    before = stored_states()
    resp = TEST_CLIENT.post(ep.STATES_EP, json=[1, 2], headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_states() == before


@patch('states.query.is_db_up', return_value=True, autospec=True)
def test_update_state_string_body(mock_is_db_up, existing_state):
    code = existing_state[sqry.STATE_CODE]
    resp = TEST_CLIENT.put(state_url(code), json='AL', headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_states()[code] == existing_state


@patch(DB_UP, return_value=True, autospec=True)
def test_create_county_number_body(mock_is_db_up):
    before = stored_counties()
    resp = TEST_CLIENT.post(ep.COUNTIES_EP, json=5, headers=AUTH_HEADERS)
    assert resp.status_code == BAD_REQUEST
    assert stored_counties() == before

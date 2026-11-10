"""
This is the file containing all of the endpoints for our flask app.
The endpoint called `endpoints` will return all available endpoints.
"""
from http import HTTPStatus

from flask import Flask, request
from flask_restx import Resource, Api, fields  # Namespace
from flask_cors import CORS

import werkzeug.exceptions as wz

import counties.fields as cflds
import counties.query as cqry
import data.db_connect as dbc
import security.security as sec
import states.fields as sflds
import states.query as sqry

app = Flask(__name__)
CORS(app)
api = Api(app)

DB_INFO_EP = '/dbinfo'
DB_INFO_RESP = 'Database:'
ENDPOINT_EP = '/endpoints'
ENDPOINT_RESP = 'Available endpoints'
HELLO_EP = '/hello'
HELLO_RESP = 'hello'
STATES_EP = '/states'
STATE_EP = f'{STATES_EP}/<state_code>'
STATES_RESP = 'States:'
STATE_FLDS_EP = f'{STATES_EP}/fields'
STATE_FLDS_RESP = 'State fields:'
COUNTIES_EP = '/counties'
COUNTY_EP = f'{COUNTIES_EP}/<state_code>/<name>'
COUNTIES_RESP = 'Counties:'
COUNTY_FLDS_EP = f'{COUNTIES_EP}/fields'
COUNTY_FLDS_RESP = 'County fields:'
MESSAGE = 'Message'
USER_ID_HDR = 'X-User-Id'
AUTH_CODE_HDR = 'X-Auth-Code'

AUTH_HDRS = api.parser()
AUTH_HDRS.add_argument(USER_ID_HDR, location='headers', required=True)
AUTH_HDRS.add_argument(AUTH_CODE_HDR, location='headers', required=True)


def check_permission(feature_name: str, action: str):
    """
    Read the user ID and auth code from the request headers and check that
    the user may perform `action` on `feature_name`.
    Raises 401 if credentials are missing, 403 if not permitted.
    """
    user_id = request.headers.get(USER_ID_HDR)
    auth_code = request.headers.get(AUTH_CODE_HDR)
    if not user_id or not auth_code:
        raise wz.Unauthorized(f'{USER_ID_HDR} and {AUTH_CODE_HDR} headers '
                              + 'are required.')
    if not sec.is_permitted(feature_name, action, user_id,
                            auth_code=auth_code):
        raise wz.Forbidden('User not permitted to do this.')


@api.route(HELLO_EP)
class HelloWorld(Resource):
    """
    The purpose of the HelloWorld class is to have a simple test to see if the
    app is working at all.
    """
    def get(self):
        """
        A trivial endpoint to see if the server is running.
        """
        return {HELLO_RESP: 'world'}


@api.route(DB_INFO_EP)
class DBInfo(Resource):
    """
    Reports which MongoDB the server uses and whether it is up.
    """
    @api.response(HTTPStatus.OK.value, 'Success')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def get(self):
        """
        Return where the database is (local or cloud), its URI (local
        only; never the cloud password), the database name, and whether
        it answers a ping. Returns 503, still with that information,
        if the database is down.
        """
        info = dbc.db_info()
        status = HTTPStatus.OK if info['up'] \
            else HTTPStatus.SERVICE_UNAVAILABLE
        return {DB_INFO_RESP: info}, status


@api.route(ENDPOINT_EP)
class Endpoints(Resource):
    """
    This class will serve as live, fetchable documentation of what endpoints
    are available in the system.
    """
    def get(self):
        """
        The `get()` method will return a sorted list of available endpoints.
        """
        endpoints = sorted(rule.rule for rule in api.app.url_map.iter_rules())
        return {"Available endpoints": endpoints}


STATE_CREATE_FLDS = api.model('CreateState', {
    sqry.STATE_CODE: fields.String(required=True),
    sqry.NAME: fields.String(required=True),
    sqry.POPULATION: fields.Integer(),
    sqry.CAPITAL: fields.String(),
    sqry.AREA: fields.Float(),
    sqry.LATITUDE: fields.Float(),
    sqry.LONGITUDE: fields.Float(),
})

STATE_UPDATE_FLDS = api.model('UpdateState', {
    sqry.NAME: fields.String(),
    sqry.POPULATION: fields.Integer(),
    sqry.CAPITAL: fields.String(),
    sqry.AREA: fields.Float(),
    sqry.LATITUDE: fields.Float(),
    sqry.LONGITUDE: fields.Float(),
})

# Fields a state request may leave out; states.query supplies defaults.
STATE_OPT_FLDS = (sqry.POPULATION, sqry.CAPITAL, sqry.AREA,
                  sqry.LATITUDE, sqry.LONGITUDE)
# Fields a state PUT may change:
STATE_UPD_FLDS = (sqry.NAME,) + STATE_OPT_FLDS


def get_json_body() -> dict:
    """
    Return the request's JSON body as a dict ({} if there is none).
    Raises 400 if the body is JSON but not an object (e.g. a list),
    since our endpoints look up fields in it by name.
    """
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise wz.BadRequest('Request body must be a JSON object.')
    return data


def optional_flds(data: dict, flds: tuple) -> dict:
    """
    Return those of flds present in a request body, so that any
    left out get their defaults from the query module.
    """
    return {fld: data[fld] for fld in flds if fld in data}


def update_args(current: dict, data: dict, flds: tuple) -> dict:
    """
    Return the fields (from flds) for a partial update: those sent in
    data replace the current ones, and the rest keep their values.
    """
    merged = {**current, **data}
    return {fld: merged[fld] for fld in flds if fld in merged}


@api.route(STATES_EP)
class States(Resource):
    """
    The get method will return a list of all states in the database.
    """
    @api.response(HTTPStatus.OK.value, 'Success')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value,
                  'Service Unavailable')
    def get(self):
        """
        The `get()` method will return a list of all states in the database.
        """
        states = sqry.read()
        if states is None:
            # if states == None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {STATES_RESP: states}

    @api.expect(AUTH_HDRS, STATE_CREATE_FLDS)
    @api.response(HTTPStatus.CREATED.value, 'Created')
    @api.response(HTTPStatus.BAD_REQUEST.value, 'Bad Request')
    @api.response(HTTPStatus.UNAUTHORIZED.value, 'Unauthorized')
    @api.response(HTTPStatus.FORBIDDEN.value, 'Forbidden')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def post(self):
        """
        Add a new state.
        Requires X-User-Id and X-Auth-Code headers.
        """
        check_permission(sec.STATES, sec.CREATE)
        data = get_json_body()
        try:
            new_state = sqry.create(data.get(sqry.STATE_CODE),
                                    data.get(sqry.NAME),
                                    **optional_flds(data, STATE_OPT_FLDS))
        except ValueError as err:
            raise wz.BadRequest(str(err))
        if new_state is None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {MESSAGE: 'State added.', STATES_RESP: new_state}, \
            HTTPStatus.CREATED


@api.route(STATE_EP)
class State(Resource):
    """
    Operations on a single state, identified by its state code.
    """
    @api.response(HTTPStatus.OK.value, 'Success')
    @api.response(HTTPStatus.NOT_FOUND.value, 'Not Found')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def get(self, state_code):
        """
        Return the state with this code, or 404 if there is none.
        No auth headers are needed to read a state.
        """
        state_exists = sqry.exists(state_code)
        if state_exists is None:
            raise wz.ServiceUnavailable('Database may be down.')
        if not state_exists:
            raise wz.NotFound(f'State {state_code} not found.')
        state = sqry.read_one(state_code)
        if state is None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {STATES_RESP: {state_code: state}}

    @api.expect(AUTH_HDRS, STATE_UPDATE_FLDS)
    @api.response(HTTPStatus.OK.value, 'Success')
    @api.response(HTTPStatus.BAD_REQUEST.value, 'Bad Request')
    @api.response(HTTPStatus.UNAUTHORIZED.value, 'Unauthorized')
    @api.response(HTTPStatus.FORBIDDEN.value, 'Forbidden')
    @api.response(HTTPStatus.NOT_FOUND.value, 'Not Found')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def put(self, state_code):
        """
        Update an existing state.
        Only the fields sent are changed; the rest keep their values.
        The state code cannot be changed.
        Requires X-User-Id and X-Auth-Code headers.
        """
        check_permission(sec.STATES, sec.UPDATE)
        data = get_json_body()
        if data.get(sqry.STATE_CODE, state_code) != state_code:
            raise wz.BadRequest('The state code cannot be changed.')
        state_exists = sqry.exists(state_code)
        if state_exists is None:
            raise wz.ServiceUnavailable('Database may be down.')
        if not state_exists:
            raise wz.NotFound(f'State {state_code} not found.')
        current = sqry.read_one(state_code)
        if current is None:
            raise wz.ServiceUnavailable('Database may be down.')
        try:
            updated = sqry.update(state_code,
                                  **update_args(current, data,
                                                STATE_UPD_FLDS))
        except ValueError as err:
            raise wz.BadRequest(str(err))
        if updated is None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {MESSAGE: 'State updated.', STATES_RESP: updated}

    @api.expect(AUTH_HDRS)
    @api.response(HTTPStatus.OK.value, 'Success')
    @api.response(HTTPStatus.UNAUTHORIZED.value, 'Unauthorized')
    @api.response(HTTPStatus.FORBIDDEN.value, 'Forbidden')
    @api.response(HTTPStatus.NOT_FOUND.value, 'Not Found')
    @api.response(HTTPStatus.CONFLICT.value, 'Conflict')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def delete(self, state_code):
        """
        Delete a state.
        A state that still has counties cannot be deleted (409 Conflict).
        Requires X-User-Id and X-Auth-Code headers.
        """
        check_permission(sec.STATES, sec.DELETE)
        state_exists = sqry.exists(state_code)
        if state_exists is None:
            raise wz.ServiceUnavailable('Database may be down.')
        if not state_exists:
            raise wz.NotFound(f'State {state_code} not found.')
        try:
            deleted = sqry.delete(state_code)
        except ValueError as err:
            raise wz.Conflict(str(err))
        if deleted is None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {MESSAGE: 'State deleted.', STATES_RESP: deleted}


@api.route(STATE_FLDS_EP)
class StateFields(Resource):
    """
    Describes the fields of a state: the data dictionary.
    """
    @api.response(HTTPStatus.OK.value, 'Success')
    def get(self):
        """
        Return the state data dictionary: for each field, its display
        name, description, type and other display information.
        """
        return {STATE_FLDS_RESP: sflds.get_flds()}


COUNTY_CREATE_FLDS = api.model('CreateCounty', {
    cqry.STATE_CODE: fields.String(required=True),
    cqry.NAME: fields.String(required=True),
    cqry.POPULATION: fields.Integer(),
    cqry.AREA: fields.Float(),
    cqry.METRO_AREA: fields.String(),
})

COUNTY_UPDATE_FLDS = api.model('UpdateCounty', {
    cqry.POPULATION: fields.Integer(),
    cqry.AREA: fields.Float(),
    cqry.METRO_AREA: fields.String(),
})

# Fields a county request may leave out; counties.query supplies
# defaults. These are also the fields a county PUT may change.
COUNTY_OPT_FLDS = (cqry.POPULATION, cqry.AREA, cqry.METRO_AREA)


@api.route(COUNTIES_EP)
class Counties(Resource):
    """
    The get method will return all counties in the database.
    """
    @api.response(HTTPStatus.OK.value, 'Success')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def get(self):
        """
        Return all counties in the database, keyed by state code,
        then by county name.
        """
        counties = cqry.read()
        if counties is None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {COUNTIES_RESP: counties}

    @api.expect(AUTH_HDRS, COUNTY_CREATE_FLDS)
    @api.response(HTTPStatus.CREATED.value, 'Created')
    @api.response(HTTPStatus.BAD_REQUEST.value, 'Bad Request')
    @api.response(HTTPStatus.UNAUTHORIZED.value, 'Unauthorized')
    @api.response(HTTPStatus.FORBIDDEN.value, 'Forbidden')
    @api.response(HTTPStatus.NOT_FOUND.value, 'Not Found')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def post(self):
        """
        Add a new county.
        Its state must already exist, else 404 Not Found.
        Requires X-User-Id and X-Auth-Code headers.
        """
        check_permission(sec.COUNTIES, sec.CREATE)
        data = get_json_body()
        try:
            new_county = cqry.create(data.get(cqry.STATE_CODE),
                                     data.get(cqry.NAME),
                                     **optional_flds(data, COUNTY_OPT_FLDS))
        except cqry.NotFoundError as err:
            raise wz.NotFound(str(err))
        except ValueError as err:
            raise wz.BadRequest(str(err))
        if new_county is None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {MESSAGE: 'County added.', COUNTIES_RESP: new_county}, \
            HTTPStatus.CREATED


@api.route(COUNTY_EP)
class County(Resource):
    """
    Operations on a single county, identified by its state code and name.
    """
    @api.expect(AUTH_HDRS, COUNTY_UPDATE_FLDS)
    @api.response(HTTPStatus.OK.value, 'Success')
    @api.response(HTTPStatus.BAD_REQUEST.value, 'Bad Request')
    @api.response(HTTPStatus.UNAUTHORIZED.value, 'Unauthorized')
    @api.response(HTTPStatus.FORBIDDEN.value, 'Forbidden')
    @api.response(HTTPStatus.NOT_FOUND.value, 'Not Found')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def put(self, state_code, name):
        """
        Update an existing county.
        Only the fields sent are changed; the rest keep their values.
        The state code and name cannot be changed.
        Requires X-User-Id and X-Auth-Code headers.
        """
        check_permission(sec.COUNTIES, sec.UPDATE)
        data = get_json_body()
        if (data.get(cqry.STATE_CODE, state_code) != state_code
                or data.get(cqry.NAME, name) != name):
            raise wz.BadRequest('The state code and name cannot be changed.')
        county_exists = cqry.exists(state_code, name)
        if county_exists is None:
            raise wz.ServiceUnavailable('Database may be down.')
        if not county_exists:
            raise wz.NotFound(f'County {name}, {state_code} not found.')
        current = cqry.read_one(state_code, name)
        if current is None:
            raise wz.ServiceUnavailable('Database may be down.')
        try:
            updated = cqry.update(state_code, name,
                                  **update_args(current, data,
                                                COUNTY_OPT_FLDS))
        except ValueError as err:
            raise wz.BadRequest(str(err))
        if updated is None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {MESSAGE: 'County updated.', COUNTIES_RESP: updated}

    @api.expect(AUTH_HDRS)
    @api.response(HTTPStatus.OK.value, 'Success')
    @api.response(HTTPStatus.UNAUTHORIZED.value, 'Unauthorized')
    @api.response(HTTPStatus.FORBIDDEN.value, 'Forbidden')
    @api.response(HTTPStatus.NOT_FOUND.value, 'Not Found')
    @api.response(HTTPStatus.SERVICE_UNAVAILABLE.value, 'Service Unavailable')
    def delete(self, state_code, name):
        """
        Delete a county.
        Requires X-User-Id and X-Auth-Code headers.
        """
        check_permission(sec.COUNTIES, sec.DELETE)
        county_exists = cqry.exists(state_code, name)
        if county_exists is None:
            raise wz.ServiceUnavailable('Database may be down.')
        if not county_exists:
            raise wz.NotFound(f'County {name}, {state_code} not found.')
        deleted = cqry.delete(state_code, name)
        if deleted is None:
            raise wz.ServiceUnavailable('Database may be down.')
        return {MESSAGE: 'County deleted.', COUNTIES_RESP: deleted}


@api.route(COUNTY_FLDS_EP)
class CountyFields(Resource):
    """
    Describes the fields of a county: the data dictionary.
    """
    @api.response(HTTPStatus.OK.value, 'Success')
    def get(self):
        """
        Return the county data dictionary: for each field, its display
        name, description, type and other display information.
        """
        return {COUNTY_FLDS_RESP: cflds.get_flds()}

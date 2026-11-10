"""
Sample states for tests, and a pytest fixture that loads them into the
states collection before each test and empties it afterwards.
To protect real data, these refuse to touch any database whose name
does not start with TEST_DB_PREFIX (tests set GEODATA_DB; see common.mk).
"""

import pytest

import data.db_connect as dbc
from states.fields import (
    AREA,
    CAPITAL,
    LATITUDE,
    LONGITUDE,
    NAME,
    POPULATION,
    STATE_CODE,
)
from states.query import STATES_COLLECT

TEST_DB_PREFIX = 'test_'

SAMPLE_STATES = {
    "AL": {
        STATE_CODE: "AL",
        POPULATION: 4903200,
        CAPITAL: "Montgomery",
        AREA: 52420,
        NAME: 'Alabama',
        LATITUDE: 32.318231,
        LONGITUDE: -86.902298,
    },
    "AK": {
        STATE_CODE: "AK",
        POPULATION: 731545,
        CAPITAL: "Juneau",
        AREA: 665384,
        NAME: 'Alaska',
        LATITUDE: 63.588753,
        LONGITUDE: -154.493062,
    },
    "AZ": {
        STATE_CODE: "AZ",
        POPULATION: 7278717,
        CAPITAL: "Phoenix",
        AREA: 113990,
        NAME: 'Arizona',
        LATITUDE: 34.048928,
        LONGITUDE: -111.093731,
    },
}


def check_test_db(db_name: str):
    """
    Raise RuntimeError unless db_name is a test database.
    """
    if not db_name.startswith(TEST_DB_PREFIX):
        raise RuntimeError(f"Refusing to change database {db_name}: "
                           + f"its name must start with {TEST_DB_PREFIX}. "
                           + f"Set {dbc.DB_ENV} (see common.mk).")


def clear_states():
    """
    Delete every state in the test database.
    (Much faster than dropping the collection before every test.)
    """
    check_test_db(dbc.SE_DB)
    dbc.connect_db()
    dbc.delete_many(STATES_COLLECT, {})


def seed_states():
    """
    Replace the states collection in the test database with SAMPLE_STATES.
    """
    clear_states()
    for state in SAMPLE_STATES.values():
        # insert a copy: MongoDB adds an _id to the doc it is given
        dbc.create(STATES_COLLECT, dict(state))


def stored_states() -> dict:
    """
    Return the states now in the test database, keyed by state code.
    This reads the database directly, so tests can check what is stored
    even while they patch is_db_up to pretend the database is down.
    """
    check_test_db(dbc.SE_DB)
    dbc.connect_db()
    return dbc.read_dict(STATES_COLLECT, STATE_CODE)


@pytest.fixture(autouse=True)
def sample_states():
    """
    Give each test a fresh copy of SAMPLE_STATES in the test database.
    """
    seed_states()
    yield
    clear_states()

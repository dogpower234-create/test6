"""
Sample counties for tests, and a pytest fixture that loads them into the
counties collection before each test and empties it afterwards.
Like states/sample_data.py, these refuse to touch any database that is
not a test database.
"""

import pytest

import data.db_connect as dbc
from counties.fields import (
    AREA,
    METRO_AREA,
    NAME,
    POPULATION,
    STATE_CODE,
)
from counties.query import COUNTIES_COLLECT, county_data
from states.sample_data import check_test_db

# County names are only unique within a state, so the data is keyed
# first by state code, then by county name.
SAMPLE_COUNTIES = {
    "AL": {
        "Autauga": {
            POPULATION: 58805,
            AREA: 594.44,
            METRO_AREA: "Montgomery, AL Metropolitan Statistical Area",
        },
        "Baldwin": {
            POPULATION: 231767,
            AREA: 1589.78,
            METRO_AREA: "Daphne-Fairhope-Foley, AL Metropolitan "
                        "Statistical Area",
        },
        "Barbour": {
            POPULATION: 25223,
            AREA: 884.88,
            METRO_AREA: "Eufaula, AL-GA Micropolitan Statistical Area",
        },
        "Bullock": {
            POPULATION: 10357,
            AREA: 622.80,
            METRO_AREA: "",
        },
    },
}


def clear_counties():
    """
    Delete every county in the test database.
    """
    check_test_db(dbc.SE_DB)
    dbc.connect_db()
    dbc.delete_many(COUNTIES_COLLECT, {})


def seed_counties():
    """
    Replace the counties collection in the test database with
    SAMPLE_COUNTIES.
    """
    clear_counties()
    for state_code, counties in SAMPLE_COUNTIES.items():
        for name, data in counties.items():
            dbc.create(COUNTIES_COLLECT,
                       {STATE_CODE: state_code, NAME: name, **data})


def stored_counties() -> dict:
    """
    Return the counties now in the test database, keyed by state code,
    then by county name. This reads the database directly, so tests can
    check what is stored even while they patch is_db_up to pretend the
    database is down.
    """
    check_test_db(dbc.SE_DB)
    dbc.connect_db()
    counties = {}
    for doc in dbc.read(COUNTIES_COLLECT):
        counties.setdefault(doc[STATE_CODE], {})[doc[NAME]] = \
            county_data(doc)
    return counties


@pytest.fixture(autouse=True)
def sample_counties():
    """
    Give each test a fresh copy of SAMPLE_COUNTIES in the test database.
    """
    seed_counties()
    yield
    clear_counties()

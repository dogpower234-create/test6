#!/usr/bin/env python3

"""
Queries on counties, stored in MongoDB through data/db_connect.py.
Each county is one document, identified by its state code and name
(county names are only unique within a state).
"""

import data.db_connect as dbc
import states.query as sqry
from states.query import needs_db
from counties.fields import (
    AREA,
    METRO_AREA,
    NAME,
    POPULATION,
    STATE_CODE,
    STATE_CODE_LEN,
)

COUNTIES_COLLECT = 'counties'

# The fields that identify a county. The rest are its data.
KEY_FLDS = (STATE_CODE, NAME)


class NotFoundError(LookupError):
    """
    Raised when something a county depends on, such as its state,
    does not exist.
    """


TEST_COUNTY = {
    STATE_CODE: "AL",
    NAME: "Test County",
    POPULATION: 50000,
    AREA: 600.5,
    METRO_AREA: "Test City, AL Metropolitan Statistical Area",
}


def county_filter(state_code: str, name: str) -> dict:
    """
    The MongoDB filter that finds one county.
    """
    return {STATE_CODE: state_code, NAME: name}


def county_data(doc: dict) -> dict:
    """
    Return a county document without its keys (state code and name)
    or MongoDB _id: just the data the API returns for a county.
    """
    return {fld: val for fld, val in doc.items()
            if fld not in KEY_FLDS and fld != dbc.MONGO_ID}


def make_county(population: int = 0, area: float = 0,
                metro_area: str = '') -> dict:
    """
    Build a county's data (everything but its keys) from its fields.
    """
    return {
        POPULATION: population,
        AREA: area,
        METRO_AREA: metro_area,
    }


@needs_db
def read():
    """
    Return all counties, keyed by state code, then by county name.
    """
    counties = {}
    for doc in dbc.read(COUNTIES_COLLECT):
        counties.setdefault(doc[STATE_CODE], {})[doc[NAME]] = \
            county_data(doc)
    return counties


@needs_db
def read_one(state_code: str, name: str):
    """
    Return the county with this state code and name,
    or None if there is none.
    """
    doc = dbc.read_one(COUNTIES_COLLECT, county_filter(state_code, name))
    return None if doc is None else county_data(doc)


@needs_db
def exists(state_code: str, name: str):
    """
    Check if a county exists.
    """
    return dbc.count(COUNTIES_COLLECT, county_filter(state_code, name)) > 0


@needs_db
def has_counties(state_code: str):
    """
    Check if a state has any counties.
    """
    return dbc.count(COUNTIES_COLLECT, {STATE_CODE: state_code}) > 0


def check_valid_county(state_code: str, name: str, population: int = 0,
                       area: float = 0, metro_area: str = '',
                       is_update: bool = False):
    """
    Raise ValueError if the county data is invalid.
    Only the state code and name are required: the other fields may
    be left at their defaults (0 or '').
    For a create, the state must exist (else NotFoundError is raised) and
    the county must not exist yet; for an update (is_update=True), the
    county must already exist.
    A county need not be in a metro area, so metro_area may be empty.
    """
    if (not isinstance(state_code, str)
            or len(state_code) != STATE_CODE_LEN
            or not all("A" <= char <= "Z" for char in state_code)):
        raise ValueError(
            f"State code must be {STATE_CODE_LEN} uppercase letters."
        )
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Name must be a non-empty string.")
    if is_update:
        if not exists(state_code, name):
            raise ValueError(f"County {name}, {state_code} does not exist.")
    else:
        if not sqry.exists(state_code):
            raise NotFoundError(f"State {state_code} not found.")
        if exists(state_code, name):
            raise ValueError(f"County {name}, {state_code} already exists.")
    if (not isinstance(population, int) or isinstance(population, bool)
            or population < 0):
        raise ValueError("Population must be a non-negative integer.")
    if (not isinstance(area, (int, float))
            or isinstance(area, bool) or area < 0):
        raise ValueError("Area must be a non-negative number.")
    if not isinstance(metro_area, str):
        raise ValueError("Metro area must be a string.")
    return True


@needs_db
def create(state_code: str, name: str, population: int = 0,
           area: float = 0, metro_area: str = ''):
    """
    Create a new county.
    Returns its data; raises ValueError if it is invalid, or
    NotFoundError if its state does not exist.
    """
    # check_valid_county raises ValueError if the county is invalid, so we
    # don't need to check the return value
    check_valid_county(state_code, name, population, area,
                       metro_area)
    county = make_county(population, area, metro_area)
    dbc.create(COUNTIES_COLLECT,
               {**county_filter(state_code, name), **county})
    return county


@needs_db
def update(state_code: str, name: str, population: int = 0,
           area: float = 0, metro_area: str = ''):
    """
    Update an existing county.
    The state code and name identify the county and cannot be changed.
    Raises ValueError if the update is invalid.
    """
    check_valid_county(state_code, name, population, area,
                       metro_area, is_update=True)
    county = make_county(population, area, metro_area)
    dbc.update(COUNTIES_COLLECT, county_filter(state_code, name),
               dict(county))
    return county


@needs_db
def delete(state_code: str, name: str):
    """
    Delete a county.
    Returns the deleted county's data, or None if it did not exist.
    """
    filt = county_filter(state_code, name)
    doc = dbc.read_one(COUNTIES_COLLECT, filt)
    if doc is None:
        return None
    dbc.delete(COUNTIES_COLLECT, filt)
    return county_data(doc)


def main():
    counties = read()
    if counties is None:
        print("Database is down.")
        return
    for state_code, state_counties in counties.items():
        for name, data in state_counties.items():
            print(f"County: {name}, {state_code}")
            print(f"Population: {data[POPULATION]}")
            print(f"Area (sq miles): {data[AREA]}")
            print(f"Metro area: {data[METRO_AREA] or '(none)'}")
            print("-" * 40)


if __name__ == "__main__":
    main()

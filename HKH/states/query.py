#!/usr/bin/env python3

"""
Queries on states, stored in MongoDB through data/db_connect.py.
Each state is one document, identified by its state code.
"""

from functools import wraps

import data.db_connect as dbc
from data.db_connect import is_db_up
from states.fields import (
    AREA,
    CAPITAL,
    LATITUDE,
    LONGITUDE,
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    NAME,
    POPULATION,
    STATE_CODE,
    STATE_CODE_LEN,
)

STATES_COLLECT = 'USStates'


def needs_db(fn):
    """
    Decorate any function that needs the database: If the DB is down,
    print a message and return None instead of calling the function;
    otherwise make sure we are connected, then call it.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_db_up():
            print("Database is down.")
            return None
        dbc.connect_db()
        return fn(*args, **kwargs)
    return wrapper


TEST_STATE = {
    STATE_CODE: "TS",
    NAME: 'Test State',
    POPULATION: 1000000,
    CAPITAL: "Test Capital",
    AREA: 50000,
    LATITUDE: 40.0,
    LONGITUDE: -100.0,
}


@needs_db
def read():
    """
    Return all states, as a dict keyed by state code.
    """
    return dbc.read_dict(STATES_COLLECT, STATE_CODE)


@needs_db
def read_one(state_code: str):
    """
    Return the state with this code, or None if there is none.
    """
    state = dbc.read_one(STATES_COLLECT, {STATE_CODE: state_code})
    if state is not None:
        del state[dbc.MONGO_ID]
    return state


@needs_db
def exists(state_code: str):
    """
    Check if a state exists.
    """
    return dbc.read_one(STATES_COLLECT, {STATE_CODE: state_code}) is not None


def is_number(val) -> bool:
    """
    True if val is an int or float (but not a bool, which Python
    counts as an int).
    """
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def check_valid_state(state_code: str, name: str, population: int = 0,
                      capital: str = '', area: float = 0,
                      latitude: float = 0, longitude: float = 0,
                      is_update: bool = False):
    """
    Raise ValueError if the state data is invalid.
    Only the state code and name are required: the other fields may
    be left at their defaults (0 or '').
    For a create, the state code must not exist yet; for an update
    (is_update=True), it must already exist.
    """
    if (not isinstance(state_code, str)
            or len(state_code) != STATE_CODE_LEN
            or not all("A" <= char <= "Z" for char in state_code)):
        raise ValueError(
            f"State code must be {STATE_CODE_LEN} uppercase letters."
        )
    if is_update:
        if not exists(state_code):
            raise ValueError(f"State code {state_code} does not exist.")
    elif exists(state_code):
        raise ValueError(f"State code {state_code} already exists.")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Name must be a non-empty string.")
    if (not isinstance(population, int)
            or isinstance(population, bool)
            or population < 0):
        raise ValueError("Population must be a non-negative integer.")
    if not isinstance(capital, str):
        raise ValueError("Capital must be a string.")
    if not is_number(area) or area < 0:
        raise ValueError("Area must be a non-negative number.")
    if (not is_number(latitude)
            or not MIN_LATITUDE <= latitude <= MAX_LATITUDE):
        raise ValueError(f"Latitude must be a number from {MIN_LATITUDE} "
                         + f"to {MAX_LATITUDE}.")
    if (not is_number(longitude)
            or not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE):
        raise ValueError(f"Longitude must be a number from {MIN_LONGITUDE} "
                         + f"to {MAX_LONGITUDE}.")
    return True


def make_state(state_code: str, name: str, population: int = 0,
               capital: str = '', area: float = 0, latitude: float = 0,
               longitude: float = 0) -> dict:
    """
    Build a state document from its fields.
    """
    return {
        STATE_CODE: state_code,
        NAME: name,
        POPULATION: population,
        CAPITAL: capital,
        AREA: area,
        LATITUDE: latitude,
        LONGITUDE: longitude,
    }


@needs_db
def create(state_code: str, name: str, population: int = 0,
           capital: str = '', area: float = 0, latitude: float = 0,
           longitude: float = 0):
    """
    Create a new state.
    Returns the new state; raises ValueError if it is invalid.
    """
    # check_valid_state raises ValueError if the state is invalid, so we don't
    # need to check the return value
    check_valid_state(state_code, name, population, capital, area,
                      latitude, longitude)
    state = make_state(state_code, name, population, capital, area,
                       latitude, longitude)
    # insert a copy: MongoDB adds an _id to the doc it is given
    dbc.create(STATES_COLLECT, dict(state))
    return state


@needs_db
def update(state_code: str, name: str, population: int = 0,
           capital: str = '', area: float = 0, latitude: float = 0,
           longitude: float = 0):
    """
    Update an existing state.
    The state code identifies the state and cannot be changed.
    Raises ValueError if the update is invalid.
    """
    check_valid_state(state_code, name, population, capital, area,
                      latitude, longitude, is_update=True)
    state = make_state(state_code, name, population, capital, area,
                       latitude, longitude)
    dbc.update(STATES_COLLECT, {STATE_CODE: state_code}, state)
    return state


@needs_db
def delete(state_code: str):
    """
    Delete a state.
    Returns the deleted state, or None if it did not exist.
    Raises ValueError if the state still has counties.
    """
    # Imported here because counties.query imports this module.
    import counties.query as cqry
    if cqry.has_counties(state_code):
        raise ValueError(f"State {state_code} still has counties.")
    state = dbc.read_one(STATES_COLLECT, {STATE_CODE: state_code})
    if state is None:
        return None
    dbc.delete(STATES_COLLECT, {STATE_CODE: state_code})
    del state[dbc.MONGO_ID]
    return state


def main():
    states = read()
    for state, data in states.items():
        print(f"State: {state}")
        print(f"Population: {data[POPULATION]}")
        print(f"Capital: {data[CAPITAL]}")
        print(f"Area (sq miles): {data[AREA]}")
        print("-" * 40)
#    print("This is the main function of query.py")


if __name__ == "__main__":
    main()

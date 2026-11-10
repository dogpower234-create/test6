#!/usr/bin/env python3
"""
Load raw_data/states.csv into the states collection in MongoDB,
replacing whatever is there. The CSV's columns are renamed to our
field names; fields the CSV lacks get '' (strings) or 0 (numbers).
"""

import csv
import sys

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

# CSV column names:
CSV_ABBREV = 'Abbrev'
CSV_LATITUDE = 'Latitude'
CSV_LONGITUDE = 'Longitude'
CSV_STATE = 'State'


def load_states(file_path):
    """
    Load states from a CSV file and return a list of dictionaries.

    Args:
        file_path (str): The path to the CSV file.
    """
    states = []
    with open(file_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            states.append(row)
    return states


def row_to_state(row: dict) -> dict:
    """
    Convert one CSV row to a state record using our field names.
    """
    return {
        STATE_CODE: row[CSV_ABBREV],
        NAME: row[CSV_STATE],
        LATITUDE: float(row[CSV_LATITUDE]),
        LONGITUDE: float(row[CSV_LONGITUDE]),
        POPULATION: 0,
        CAPITAL: '',
        AREA: 0,
    }


def store_states(states: list, collection=STATES_COLLECT) -> int:
    """
    Replace the contents of the states collection with `states`.
    Returns the number of states stored.
    """
    dbc.connect_db()
    dbc.drop(collection)
    for state in states:
        dbc.create(collection, state)
    return len(states)


def main():
    # accept the file path as an argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        print("USAGE: python load.py <path_to_states_csv>")
        sys.exit(1)

    states = [row_to_state(row) for row in load_states(file_path)]
    count = store_states(states)
    print(f"Stored {count} states in {dbc.SE_DB}.{STATES_COLLECT}.")


if __name__ == "__main__":
    main()

"""
The data dictionary for states.
Shared constants and field names come from common/fields.py.
"""

from common.fields import (
    AREA,
    DEC_PLACES,
    DESCR,
    DISP_NAME,
    FLD_TYPE,
    FLOAT,
    INT,
    JUSTIFICATION,
    MAX_LEN,
    NAME,
    POPULATION,
    RIGHT,
    STATE_CODE,
    STATE_CODE_LEN,
    STR,
)

# State-only field names:
CAPITAL = 'capital'
LATITUDE = 'latitude'
LONGITUDE = 'longitude'

# Field values:
MIN_LATITUDE = -90
MAX_LATITUDE = 90
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180

STATE_FLDS = {
    STATE_CODE: {
        DISP_NAME: 'State Code',
        DESCR: 'The two-letter postal code for the state.',
        FLD_TYPE: STR,
        MAX_LEN: STATE_CODE_LEN,
    },
    NAME: {
        DISP_NAME: 'Name',
        DESCR: 'The name of the state.',
        FLD_TYPE: STR,
    },
    CAPITAL: {
        DISP_NAME: 'Capital',
        DESCR: 'The capital city of the state.',
        FLD_TYPE: STR,
    },
    POPULATION: {
        DISP_NAME: 'Population',
        DESCR: 'The number of people living in the state.',
        FLD_TYPE: INT,
        JUSTIFICATION: RIGHT,
    },
    AREA: {
        DISP_NAME: 'Area (sq miles)',
        DESCR: 'The total area of the state in square miles.',
        FLD_TYPE: FLOAT,
        DEC_PLACES: 2,
        JUSTIFICATION: RIGHT,
    },
    LATITUDE: {
        DISP_NAME: 'Latitude',
        DESCR: 'The latitude of the center of the state, in degrees '
               + '(-90 to 90).',
        FLD_TYPE: FLOAT,
        DEC_PLACES: 6,
        JUSTIFICATION: RIGHT,
    },
    LONGITUDE: {
        DISP_NAME: 'Longitude',
        DESCR: 'The longitude of the center of the state, in degrees '
               + '(-180 to 180).',
        FLD_TYPE: FLOAT,
        DEC_PLACES: 6,
        JUSTIFICATION: RIGHT,
    },
}


def get_flds():
    """Return the state field dictionary."""
    return STATE_FLDS

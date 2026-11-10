"""
The data dictionary for counties.
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

# County-only field names:
METRO_AREA = 'metro_area'

COUNTY_FLDS = {
    STATE_CODE: {
        DISP_NAME: 'State Code',
        DESCR: 'The two-letter postal code for the state the county is in.',
        FLD_TYPE: STR,
        MAX_LEN: STATE_CODE_LEN,
    },
    NAME: {
        DISP_NAME: 'Name',
        DESCR: 'The name of the county, unique within its state.',
        FLD_TYPE: STR,
    },
    POPULATION: {
        DISP_NAME: 'Population',
        DESCR: 'The number of people living in the county.',
        FLD_TYPE: INT,
        JUSTIFICATION: RIGHT,
    },
    AREA: {
        DISP_NAME: 'Area (sq miles)',
        DESCR: 'The total area of the county in square miles.',
        FLD_TYPE: FLOAT,
        DEC_PLACES: 2,
        JUSTIFICATION: RIGHT,
    },
    METRO_AREA: {
        DISP_NAME: 'Metro Area',
        DESCR: 'The metropolitan or micropolitan statistical area the '
               + 'county is in, or empty if none.',
        FLD_TYPE: STR,
    },
}


def get_flds():
    """Return the county field dictionary."""
    return COUNTY_FLDS

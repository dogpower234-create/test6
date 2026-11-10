import pytest

import counties.fields as flds
import counties.query as qry
from counties.sample_data import SAMPLE_COUNTIES
import common.fields as cmn


def test_fields_match_test_county():
    """
    The data dictionary and the test county must describe the same fields.
    """
    assert set(flds.COUNTY_FLDS) == set(qry.TEST_COUNTY)


def test_fields_match_county_data():
    """
    Every sample county has exactly the non-key fields in the dictionary.
    The state code and name are the keys.
    """
    non_key_flds = set(flds.COUNTY_FLDS) - {flds.STATE_CODE, flds.NAME}
    for counties in SAMPLE_COUNTIES.values():
        for data in counties.values():
            assert set(data) == non_key_flds


@pytest.mark.parametrize('fld_nm', list(flds.COUNTY_FLDS))
def test_field_is_described(fld_nm):
    fld = flds.COUNTY_FLDS[fld_nm]
    assert fld[flds.DISP_NAME]
    assert fld[flds.DESCR]
    assert fld[flds.FLD_TYPE] in (flds.STR, flds.INT, flds.FLOAT)


def test_state_code_max_len():
    state_code = flds.COUNTY_FLDS[flds.STATE_CODE]
    assert state_code[flds.MAX_LEN] == flds.STATE_CODE_LEN


@pytest.mark.parametrize('const', ['STATE_CODE', 'NAME', 'POPULATION',
                                   'AREA', 'STATE_CODE_LEN'])
def test_shared_fields_from_common(const):
    assert getattr(flds, const) is getattr(cmn, const)


def test_query_uses_fields_constants():
    assert qry.STATE_CODE is flds.STATE_CODE
    assert qry.METRO_AREA is flds.METRO_AREA
    assert qry.STATE_CODE_LEN == flds.STATE_CODE_LEN


def test_get_flds():
    assert isinstance(flds.get_flds(), dict)
    for fld_nm, fld in flds.get_flds().items():
        assert isinstance(fld, dict)

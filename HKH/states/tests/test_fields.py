import pytest

import common.fields as cmn
import states.fields as flds
import states.query as qry
from states.sample_data import stored_states


def test_fields_match_test_state():
    """
    The data dictionary and the test state must describe the same fields.
    """
    assert set(flds.STATE_FLDS) == set(qry.TEST_STATE)


def test_fields_match_state_data():
    """
    Every stored state has exactly the fields in the dictionary.
    """
    for data in stored_states().values():
        assert set(data) == set(flds.STATE_FLDS)


@pytest.mark.parametrize('fld_nm', list(flds.STATE_FLDS))
def test_field_is_described(fld_nm):
    fld = flds.STATE_FLDS[fld_nm]
    assert fld[flds.DISP_NAME]
    assert fld[flds.DESCR]
    assert fld[flds.FLD_TYPE] in (flds.STR, flds.INT, flds.FLOAT)


def test_state_code_max_len():
    state_code = flds.STATE_FLDS[flds.STATE_CODE]
    assert state_code[flds.MAX_LEN] == flds.STATE_CODE_LEN


@pytest.mark.parametrize('const', ['STATE_CODE', 'NAME', 'POPULATION',
                                   'AREA', 'STATE_CODE_LEN'])
def test_shared_fields_from_common(const):
    assert getattr(flds, const) is getattr(cmn, const)


def test_query_uses_fields_constants():
    assert qry.STATE_CODE is flds.STATE_CODE
    assert qry.STATE_CODE_LEN == flds.STATE_CODE_LEN


def test_get_flds():
    assert isinstance(flds.get_flds(), dict)
    for fld_nm, fld in flds.get_flds().items():
        assert isinstance(fld, dict)

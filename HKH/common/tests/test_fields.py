import common.fields as flds

SHARED_FLD_NMS = [flds.NAME, flds.STATE_CODE, flds.POPULATION, flds.AREA]


def test_shared_field_names_distinct():
    assert len(set(SHARED_FLD_NMS)) == len(SHARED_FLD_NMS)


def test_shared_field_names_are_strings():
    for fld_nm in SHARED_FLD_NMS:
        assert isinstance(fld_nm, str) and fld_nm


def test_field_types_distinct():
    types = [flds.STR, flds.INT, flds.FLOAT]
    assert len(set(types)) == len(types)


def test_state_code_len():
    assert isinstance(flds.STATE_CODE_LEN, int)
    assert flds.STATE_CODE_LEN > 0

def test_justification_values_distinct():
    assert flds.LEFT != flds.RIGHT

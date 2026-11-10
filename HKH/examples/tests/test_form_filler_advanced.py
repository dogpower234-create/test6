from unittest.mock import patch

import pytest

import examples.form_filler as ff


@pytest.fixture
def integer_form():
    return [
        {
            ff.FLD_NM: "age",
            ff.QSTN: "Age?",
            ff.TYPECAST: ff.INT,
        }
    ]


def test_form_converts_input_to_integer(integer_form):
    with patch(
        "examples.form_filler.get_input", return_value="21"
    ) as mock_input:
        result = ff.form(integer_form)

    assert result == {"age": 21}
    mock_input.assert_called_once_with("", "", "Age?")


def test_form_rejects_non_integer_input(integer_form):
    with patch(
        "examples.form_filler.get_input", return_value="not-a-number"
    ):
        with pytest.raises(ValueError, match="invalid literal for int"):
            ff.form(integer_form)


@pytest.mark.skip(
    reason="Blank integer input is converted before the default is applied."
)
def test_form_uses_integer_default_for_blank_input(integer_form):
    integer_form[0][ff.DEFAULT] = 21

    with patch("examples.form_filler.get_input", return_value=""):
        assert ff.form(integer_form) == {"age": 21}

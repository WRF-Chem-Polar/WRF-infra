# Copyright (c) 2026-now LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Common Python resources for WRF-infra: tests for namelist module."""

import pytest
from namelist import (
    Value,
    Namelist,
    _name_is_valid,
    _process_value,
    _parse_key_values,
)


class TestNameIsValid:
    def test_valid_01(self):
        assert _name_is_valid("section_name") is True

    def test_valid_02(self):
        assert _name_is_valid("section3_name") is True

    def test_valid_03(self):
        assert _name_is_valid("section3") is True

    def test_valid_04(self):
        assert _name_is_valid("section_name_bis") is True

    def test_valid_05(self):
        assert _name_is_valid("SECTION") is True

    def test_invalid_01(self):
        assert _name_is_valid("2_section_name") is False

    def test_invalid_02(self):
        assert _name_is_valid("section__name") is False

    def test_invalid_03(self):
        assert _name_is_valid("_section_name") is False

    def test_invalid_04(self):
        assert _name_is_valid("section-name") is False

    def test_invalid_05(self):
        assert _name_is_valid("section name") is False

    def test_invalid_06(self):
        assert _name_is_valid("123") is False

    def test_invalid_07(self):
        assert _name_is_valid("") is False

    def test_invalid_08(self):
        assert _name_is_valid("_") is False

    def test_invalid_09(self):
        assert _name_is_valid("&") is False


class TestProcessValue:
    def test_01(self):
        assert _process_value(".true.") == Value(True)

    def test_02(self):
        assert _process_value(".false.") == Value(False)

    def test_03(self):
        assert _process_value("12") == Value(12)

    def test_04(self):
        assert _process_value("0012") == Value(12)

    def test_05(self):
        assert _process_value("1.2") == Value(1.2)

    def test_06(self):
        assert _process_value("001.20") == Value(1.2)

    def test_07(self):
        assert _process_value("-12") == Value(-12)

    def test_08(self):
        assert _process_value("'-12'") == Value("-12", quoting=True)

    def test_09(self):
        assert _process_value('"-12"') == Value("-12", quoting=True)

    def test_10(self):
        with pytest.raises(ValueError):
            _process_value("'-12")

    def test_11(self):
        with pytest.raises(ValueError):
            _process_value("-12'")

    def test_12(self):
        with pytest.raises(ValueError):
            _process_value('"-12')

    def test_13(self):
        with pytest.raises(ValueError):
            _process_value('-12"')

    def test_14(self):
        with pytest.raises(ValueError):
            _process_value("'")

    def test_15(self):
        with pytest.raises(ValueError):
            _process_value('"')


class TestParseKeyValues:
    def test_one_value_01(self):
        result = _parse_key_values("start_date = 2026-05-15")
        expected = ("start_date", [Value("2026-05-15", quoting=False)])
        assert result == expected

    def test_one_value_02(self):
        result = _parse_key_values("start_date = '2026-05-15'")
        expected = ("start_date", [Value("2026-05-15")])
        assert result == expected

    def test_one_value_03(self):
        result = _parse_key_values('start_date = "2026-05-15"')
        expected = ("start_date", [Value("2026-05-15")])
        assert result == expected

    def test_one_value_04(self):
        result = _parse_key_values("the_answer = 42")
        expected = ("the_answer", [Value(42)])
        assert result == expected

    def test_one_value_05(self):
        result = _parse_key_values("i_like_pi = 3.14")
        expected = ("i_like_pi", [Value(3.14)])
        assert result == expected

    def test_one_value_06(self):
        result = _parse_key_values("i_like_pi_as_str = '3.14'")
        expected = ("i_like_pi_as_str", [Value("3.14", quoting=True)])
        assert result == expected

    def test_one_value_07(self):
        result = _parse_key_values("a_bool_value = .true.")
        expected = ("a_bool_value", [Value(True)])
        assert result == expected

    def test_one_value_08(self):
        result = _parse_key_values("a_bool_value = .false.")
        expected = ("a_bool_value", [Value(False)])
        assert result == expected

    def test_one_value_09(self):
        result = _parse_key_values("a_quoted_bool_value = '.false.'")
        expected = ("a_quoted_bool_value", [Value(".false.")])
        assert result == expected

    def test_multi_values_01(self):
        result = _parse_key_values("some_values = 10, 3.14, '9.1', 2026-05-15")
        expected = (
            "some_values",
            [
                Value(10),
                Value(3.14),
                Value("9.1", quoting=True),
                Value("2026-05-15", quoting=False),
            ],
        )
        assert result == expected

    def test_weird_spacing_01(self):
        result = _parse_key_values(" some_values    =    10 , .true.,  3.14  ")
        expected = ("some_values", [Value(10), Value(True), Value(3.14)])
        assert result == expected

    def test_trailing_commas_01(self):
        result = _parse_key_values("some_values = 10, 3.14,")
        expected = ("some_values", [Value(10), Value(3.14)])
        assert result == expected

    def test_trailing_commas_02(self):
        result = _parse_key_values("some_values = 10, 3.14,,,")
        expected = ("some_values", [Value(10), Value(3.14)])
        assert result == expected

    def test_bad_equal_signs_01(self):
        with pytest.raises(ValueError):
            _parse_key_values("some_values == 2.1, 3")

    def test_bad_equal_signs_02(self):
        with pytest.raises(ValueError):
            _parse_key_values("some_values = 2.1, 3 =")

    def test_bad_equal_signs_03(self):
        with pytest.raises(ValueError):
            _parse_key_values("= some_values = 2.1, 3")

    def test_bad_equal_signs_04(self):
        with pytest.raises(ValueError):
            _parse_key_values("some_values <- 2.1, 3")

    def test_bad_key_name_01(self):
        with pytest.raises(ValueError):
            _parse_key_values("some values = 2.1, 3")

    def test_bad_key_name_02(self):
        with pytest.raises(ValueError):
            _parse_key_values(" = 2.1, 3")


class TestIntegrationNamelist:
    def test_only_one_section_01(self):
        namelist_str = """&the_only_section
    some_dates    = 2025-05-15, 2025-06-15, 2025-07-15
    some_integers = 1         , 2         , 3
    some_float    = 3.14      , 4.15      , 5.16
    some_booleans = .true.    , .true.    , .false.
    a_mix         = 2025-05-15, 1         , 3.14
    some_quotes   = 1         , '2'       , 3
/"""
        namelist = Namelist()
        namelist.parse(namelist_str)
        assert str(namelist) == namelist_str

    def test_two_sections_01(self):
        namelist_str = """&first_section
    some_dates    = 2025-05-15, 2025-06-15, 2025-07-15
    some_integers = 1         , 2         , 3
    some_float    = 3.14      , 4.15      , 5.16
    some_booleans = .true.    , .true.    , .false.
    a_mix         = 2025-05-15, 1         , 3.14
    some_quotes   = 1         , '2'       , 3
/

&second_section
    one_value     = 3
    another_value = 4
/"""
        namelist = Namelist()
        namelist.parse(namelist_str)
        assert str(namelist) == namelist_str

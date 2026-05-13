# Copyright (c) 2026-now LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Common Python resources for WRF-infra: tests for namelist module."""

import pytest
from namelist import Value, _name_is_valid, _process_value


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
        assert _process_value("'-12'") == Value(-12, quoting=True)

    def test_09(self):
        assert _process_value('"-12"') == Value(-12, quoting=True)

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

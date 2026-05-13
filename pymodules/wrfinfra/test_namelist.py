# Copyright (c) 2026-now LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Common Python resources for WRF-infra: tests for namelist module."""

from namelist import _name_is_valid


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

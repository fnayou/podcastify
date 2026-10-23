#!/usr/bin/env python3
"""Tests for utility/helper functions."""

import pytest

from podcastify.parser import _coerce_bool, _is_valid_name


class TestCoerceBool:
    def test_none_returns_default(self):
        assert _coerce_bool(None) is False
        assert _coerce_bool(None, True) is True

    def test_actual_bool(self):
        assert _coerce_bool(True) is True
        assert _coerce_bool(False) is False

    def test_string_true(self):
        assert _coerce_bool("true") is True
        assert _coerce_bool("True") is True
        assert _coerce_bool("TRUE") is True

    def test_string_yes(self):
        assert _coerce_bool("yes") is True
        assert _coerce_bool("Yes") is True

    def test_string_one(self):
        assert _coerce_bool("1") is True
        assert _coerce_bool("on") is True

    def test_string_false(self):
        assert _coerce_bool("false") is False
        assert _coerce_bool("False") is False
        assert _coerce_bool("FALSE") is False

    def test_string_no(self):
        assert _coerce_bool("no") is False
        assert _coerce_bool("No") is False

    def test_string_zero(self):
        assert _coerce_bool("0") is False
        assert _coerce_bool("off") is False

    def test_int(self):
        assert _coerce_bool(1) is True
        assert _coerce_bool(0) is False
        assert _coerce_bool(42) is True

    def test_list(self):
        assert _coerce_bool([]) is False
        assert _coerce_bool([1]) is True

    def test_whitespace(self):
        assert _coerce_bool("  true  ") is True
        assert _coerce_bool(" false ") is False


class TestIsValidName:
    @pytest.mark.parametrize("name", ["myshow", "My_Show-2", "show.v2", "a", "9lives"])
    def test_valid(self, name):
        assert _is_valid_name(name) is True

    @pytest.mark.parametrize(
        "name",
        ["", "..", "../../etc", "foo/bar", "foo\\bar", "my..show", "my show", "a#b", "a?b", "a%b", "café", "-a", ".a", "_a", "a\n"],
    )
    def test_invalid(self, name):
        assert _is_valid_name(name) is False

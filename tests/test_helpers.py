#!/usr/bin/env python3
"""Tests for utility/helper functions."""

import pytest

from podcastify.config import Config, _coerce_bool
from podcastify.parser import _is_valid_name


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

    def test_empty_string_is_false_without_warning(self, caplog):
        assert _coerce_bool("") is False
        assert not caplog.records

    @pytest.mark.parametrize("value", ["banana", "2", "tru"])
    def test_unknown_string_warns_and_is_false(self, value, caplog):
        assert _coerce_bool(value) is False
        assert any(value in r.message and r.levelname == "WARNING" for r in caplog.records)

    @pytest.mark.parametrize("value", ["true", "no", "ON", 1, None, True])
    def test_known_values_do_not_warn(self, value, caplog):
        _coerce_bool(value)
        assert not caplog.records


class TestEnvBooleans:
    @pytest.mark.parametrize("name", ["PUBLISH_XML", "RUN_ON_START"])
    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
    def test_truthy(self, monkeypatch, name, value):
        monkeypatch.setenv(name, value)
        assert getattr(Config, name) is True

    @pytest.mark.parametrize("name", ["PUBLISH_XML", "RUN_ON_START"])
    @pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "off"])
    def test_falsy(self, monkeypatch, name, value):
        monkeypatch.setenv(name, value)
        assert getattr(Config, name) is False

    @pytest.mark.parametrize("name", ["PUBLISH_XML", "RUN_ON_START"])
    def test_unknown_value_warns_and_is_false(self, monkeypatch, caplog, name):
        monkeypatch.setenv(name, "banana")
        assert getattr(Config, name) is False
        assert any("banana" in r.message and r.levelname == "WARNING" for r in caplog.records)

    @pytest.mark.parametrize("name", ["PUBLISH_XML", "RUN_ON_START"])
    def test_unset_defaults_to_true(self, monkeypatch, name):
        monkeypatch.delenv(name)
        assert getattr(Config, name) is True


class TestIsValidName:
    @pytest.mark.parametrize("name", ["myshow", "My_Show-2", "show.v2", "a", "9lives"])
    def test_valid(self, name):
        assert _is_valid_name(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "..",
            "../../etc",
            "foo/bar",
            "foo\\bar",
            "my..show",
            "my show",
            "a#b",
            "a?b",
            "a%b",
            "café",
            "-a",
            ".a",
            "_a",
            "a\n",
        ],
    )
    def test_invalid(self, name):
        assert _is_valid_name(name) is False

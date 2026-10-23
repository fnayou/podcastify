#!/usr/bin/env python3
"""Tests for logging configuration."""

import logging

import pytest

from podcastify.cli import main
from podcastify.logging_config import configure_logging


def _package_logger():
    return logging.getLogger("podcastify")


class TestConfigureLogging:
    def test_handlers_live_on_the_package_logger(self):
        configure_logging()
        assert len(_package_logger().handlers) == 2
        assert logging.getLogger("podcastify.cli").handlers == []

    def test_idempotent(self):
        configure_logging()
        configure_logging()
        assert len(_package_logger().handlers) == 2

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("ERROR", logging.ERROR),
            ("INFO", logging.INFO),
            ("DEBUG", logging.DEBUG),
            ("debug", logging.DEBUG),
            ("INVALID", logging.INFO),
        ],
    )
    def test_level_from_environment(self, monkeypatch, value, expected):
        monkeypatch.setenv("LOG_LEVEL", value)
        configure_logging()
        assert _package_logger().level == expected

    def test_level_is_read_at_call_time(self, monkeypatch):
        configure_logging()
        assert _package_logger().level == logging.INFO
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        configure_logging()
        assert _package_logger().level == logging.DEBUG

    def test_explicit_level_wins(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        configure_logging("ERROR")
        assert _package_logger().level == logging.ERROR

    def test_formatter_is_iso_8601(self):
        configure_logging()
        for handler in _package_logger().handlers:
            assert "%(asctime)s" in handler.formatter._fmt
            assert handler.formatter.datefmt == "%Y-%m-%dT%H:%M:%S"

    def test_warning_goes_to_stderr_and_info_to_stdout(self, capsys):
        configure_logging()
        logger = logging.getLogger("podcastify.cli")
        logger.info("info line")
        logger.warning("warning line")
        out, err = capsys.readouterr()
        assert "info line" in out and "warning line" not in out
        assert "warning line" in err and "info line" not in err

    def test_no_duplicate_lines_when_root_is_configured(self, capsys):
        root_stream = logging.StreamHandler()
        root = logging.getLogger()
        root.addHandler(root_stream)
        try:
            configure_logging()
            logging.getLogger("podcastify.cli").warning("only once")
        finally:
            root.removeHandler(root_stream)
        out, err = capsys.readouterr()
        assert (out + err).count("only once") == 1


class TestMainConfiguresLogging:
    def test_main_installs_handlers(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        assert main(["generate"]) == 0
        assert len(_package_logger().handlers) == 2
        assert "No podcast configurations found" in capsys.readouterr().out

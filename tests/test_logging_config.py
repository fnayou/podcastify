#!/usr/bin/env python3
"""Tests for logging configuration."""

import logging

from podcastify.logging_config import get_logger, reset_logger_cache


class TestGetLogger:
    def test_get_logger_returns_logger(self):
        reset_logger_cache()
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test"

    def test_get_logger_idempotent(self):
        reset_logger_cache()
        logger1 = get_logger("test")
        handler_count_1 = len(logger1.handlers)
        logger2 = get_logger("test")
        handler_count_2 = len(logger2.handlers)
        assert logger1 is logger2
        assert handler_count_1 == handler_count_2

    def test_get_logger_has_handlers(self):
        reset_logger_cache()
        logger = get_logger("test")
        assert len(logger.handlers) > 0

    def test_get_logger_default_name(self):
        reset_logger_cache()
        logger = get_logger()
        assert logger.name == "podcastify"

    def test_level_filtering_error_only(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        reset_logger_cache()
        logger = get_logger("test")
        assert logger.level == logging.ERROR

    def test_level_filtering_info(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        reset_logger_cache()
        logger = get_logger("test")
        assert logger.level == logging.INFO

    def test_level_filtering_debug(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        reset_logger_cache()
        logger = get_logger("test")
        assert logger.level == logging.DEBUG

    def test_invalid_log_level_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        reset_logger_cache()
        logger = get_logger("test")
        assert logger.level == logging.INFO

    def test_case_insensitive_level(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "debug")
        reset_logger_cache()
        logger = get_logger("test")
        assert logger.level == logging.DEBUG

    def test_formatter_includes_timestamp(self):
        reset_logger_cache()
        logger = get_logger("test")
        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert handler.formatter is not None
        assert "%(asctime)s" in handler.formatter._fmt

    def test_formatter_iso_8601_format(self):
        reset_logger_cache()
        logger = get_logger("test")
        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert handler.formatter is not None
        assert "%Y-%m-%dT%H:%M:%S" == handler.formatter.datefmt

    def test_stderr_handler_warning_level(self):
        reset_logger_cache()
        logger = get_logger("test")
        stderr_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stderr_handlers) > 0
        stderr_handler = [h for h in stderr_handlers if h.level == logging.WARNING]
        assert len(stderr_handler) == 1

import logging
import sys
from typing import Optional


_logger_cache = {}


def get_logger(name: str = "podcastify") -> logging.Logger:
    """
    Get or create a configured logger with idempotent handler setup.

    WARNING+ routes to stderr, INFO/DEBUG to stdout.
    Idempotency: if logger already has handlers, reuse them (no duplication
    across repeated calls or tests).

    Args:
        name: Logger name (default "podcastify").

    Returns:
        Configured logging.Logger instance.
    """
    if name in _logger_cache:
        return _logger_cache[name]

    logger = logging.getLogger(name)

    if logger.handlers:
        _logger_cache[name] = logger
        return logger

    from podcastify.config import Config

    level_str = Config.LOG_LEVEL.upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}

    if level_str not in valid_levels:
        level_str = "INFO"

    logger.setLevel(getattr(logging, level_str))

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    logger.propagate = True

    _logger_cache[name] = logger
    return logger


def reset_logger_cache() -> None:
    """Reset the logger cache (useful for tests)."""
    global _logger_cache
    for logger_name in list(_logger_cache.keys()):
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    _logger_cache.clear()

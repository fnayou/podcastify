import logging
import sys
from typing import Optional

from podcastify.config import Config

PACKAGE_LOGGER = "podcastify"
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


def configure_logging(level: Optional[str] = None) -> None:
    level_str = (level or Config.LOG_LEVEL).upper()
    if level_str not in VALID_LEVELS:
        level_str = "INFO"

    logger = logging.getLogger(PACKAGE_LOGGER)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
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

    logger.propagate = False

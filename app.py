#!/usr/bin/env python3
"""Entry point for Podcastify RSS generator (delegates to podcastify package)."""

import sys

from podcastify.cli import main

__all__ = [
    "Config",
    "MediaProcessor",
    "ConfigurationManager",
    "EpisodeManager",
    "RSSGenerator",
    "PodcastProcessor",
    "main",
    "_coerce_bool",
    "_is_valid_name",
]

from podcastify import (  # noqa: E402
    Config,
    ConfigurationManager,
    EpisodeManager,
    MediaProcessor,
    PodcastProcessor,
    RSSGenerator,
    _coerce_bool,
    _is_valid_name,
)

if __name__ == "__main__":
    sys.exit(main())

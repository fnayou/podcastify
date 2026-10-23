#!/usr/bin/env python3
"""Entry point for Podcastify RSS generator (delegates to podcastify package)."""

import sys

from podcastify.cli import main

if __name__ == "__main__":
    sys.exit(main())

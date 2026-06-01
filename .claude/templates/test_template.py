#!/usr/bin/env python3
"""Tests for <ComponentName>."""

from unittest.mock import MagicMock

import pytest

from podcastify.<module> import <ClassName>


class Test<ClassName>:
    def test_example(self, mocker):
        mocker.patch(
            "podcastify.<module>.subprocess.run",
            return_value=MagicMock(stdout="1234.5\n", stderr=""),
        )
        assert True

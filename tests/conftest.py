#!/usr/bin/env python3
"""Shared fixtures for podcastify tests."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    """Reset environment variables to defaults before each test."""
    monkeypatch.setenv("PODCASTS_ROOT", "/app/podcasts")
    monkeypatch.setenv("PUBLIC_ROOT", "/app/public")
    monkeypatch.setenv("CACHE_ROOT", "/app/.cache")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8080")
    monkeypatch.setenv("PUBLISH_XML", "true")
    monkeypatch.setenv("RUN_ON_START", "true")


@pytest.fixture
def tmp_podcasts_dir(tmp_path):
    """Return a temporary podcasts directory."""
    d = tmp_path / "podcasts"
    d.mkdir()
    return d


@pytest.fixture
def tmp_public_dir(tmp_path):
    """Return a temporary public directory."""
    d = tmp_path / "public"
    d.mkdir()
    return d


@pytest.fixture
def sample_flat_config():
    """Return a flat podcast config dict."""
    return {
        "name": "myshow",
        "title": "My Show",
        "author-name": "Test Author",
        "author-email": "test@example.com",
        "description": "Test description",
        "language": "en",
        "explicit": False,
        "image": "cover.jpg",
        "categories": ["Technology"],
        "episodes": [
            {"file": "ep01.mp3", "title": "Episode 1", "description": "First"},
        ],
    }


@pytest.fixture
def sample_nested_config():
    """Return a nested podcast config dict (wrapped under 'podcast' key)."""
    return {
        "podcast": {
            "name": "nested",
            "title": "Nested Show",
            "author-name": "Nested Author",
            "description": "Nested desc",
            "episodes": [],
        }
    }


@pytest.fixture
def sample_legacy_config():
    """Return a legacy config using 'author' instead of 'author-name'."""
    return {
        "title": "Legacy Show",
        "author": "Legacy Author",
        "description": "Legacy desc",
    }


@pytest.fixture
def mock_mp3(tmp_path):
    """Create a dummy MP3 file and return its path."""
    mp3 = tmp_path / "dummy.mp3"
    mp3.write_bytes(b"\x00" * 1024)
    return mp3

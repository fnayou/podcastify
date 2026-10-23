#!/usr/bin/env python3
"""Shared fixtures for podcastify tests."""

import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def reset_env(monkeypatch, tmp_path):
    """Reset environment variables to defaults before each test."""
    app_root = tmp_path / "app"
    monkeypatch.setenv("PODCASTS_ROOT", str(app_root / "podcasts"))
    monkeypatch.setenv("PUBLIC_ROOT", str(app_root / "public"))
    monkeypatch.setenv("CACHE_ROOT", str(app_root / ".cache"))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8080")
    monkeypatch.setenv("PUBLISH_XML", "true")
    monkeypatch.setenv("RUN_ON_START", "true")
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.fixture(autouse=True)
def reset_package_logger():
    """Give every test an unconfigured package logger at INFO."""
    logger = logging.getLogger("podcastify")

    def reset():
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.propagate = True
        logger.setLevel(logging.INFO)

    reset()
    yield
    reset()


def _reset_media_state():
    from podcastify.media import MediaProcessor
    MediaProcessor._duration_cache.clear()
    MediaProcessor._unpersisted.clear()
    MediaProcessor._disk_loaded = False
    MediaProcessor._ffprobe_missing_warned = False


@pytest.fixture(autouse=True)
def reset_media_state():
    """Reset MediaProcessor class state before and after each test."""
    _reset_media_state()
    yield
    _reset_media_state()


@pytest.fixture(autouse=True)
def mock_ffprobe(mocker):
    """Stub ffprobe so no test depends on the real binary."""
    return mocker.patch(
        "podcastify.media.subprocess.run",
        return_value=subprocess.CompletedProcess(args=["ffprobe"], returncode=0, stdout="42.0\n", stderr=""),
    )


GOLDEN_NOW = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.fixture
def frozen_clock(mocker):
    """Pin the feed's lastBuildDate clock to GOLDEN_NOW."""

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return GOLDEN_NOW.astimezone(tz) if tz else GOLDEN_NOW.replace(tzinfo=None)

    mocker.patch("podcastify.rss.datetime", FrozenDatetime)
    return GOLDEN_NOW


@pytest.fixture
def golden_roots(monkeypatch, tmp_path):
    """Point Config at tmp podcasts and public roots and return them."""
    podcasts = tmp_path / "golden_podcasts"
    public = tmp_path / "golden_public"
    podcasts.mkdir()
    public.mkdir()
    monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", podcasts)
    monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public)
    monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
    return podcasts, public


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

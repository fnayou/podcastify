#!/usr/bin/env python3
"""Tests for Config class."""

from pathlib import Path

from podcastify.config import Config


class TestConfigDefaults:
    def test_default_podcasts_root(self):
        assert Config.PODCASTS_ROOT == Path("/app/podcasts")

    def test_default_public_root(self):
        assert Config.PUBLIC_ROOT == Path("/app/public")

    def test_default_base_url(self):
        assert Config.BASE_URL == "http://localhost:8080"

    def test_default_publish_xml(self):
        assert Config.PUBLISH_XML is True

    def test_default_run_on_start(self):
        assert Config.RUN_ON_START is True

    def test_channel_fields(self):
        assert "name" in Config.CHANNEL_FIELDS
        assert "title" in Config.CHANNEL_FIELDS
        assert "categories" in Config.CHANNEL_FIELDS

    def test_episode_fields(self):
        assert "title" in Config.EPISODE_FIELDS
        assert "guid" in Config.EPISODE_FIELDS
        assert "duration_hms" in Config.EPISODE_FIELDS


class TestConfigFromEnv:
    def test_custom_podcasts_root(self, monkeypatch):
        monkeypatch.setenv("PODCASTS_ROOT", "/custom/podcasts")
        assert Config.PODCASTS_ROOT == Path("/custom/podcasts")

    def test_custom_public_root(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_ROOT", "/custom/public")
        assert Config.PUBLIC_ROOT == Path("/custom/public")

    def test_custom_base_url(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com")
        assert Config.BASE_URL == "https://example.com"

    def test_publish_xml_false(self, monkeypatch):
        monkeypatch.setenv("PUBLISH_XML", "false")
        assert Config.PUBLISH_XML is False

    def test_run_on_start_false(self, monkeypatch):
        monkeypatch.setenv("RUN_ON_START", "false")
        assert Config.RUN_ON_START is False

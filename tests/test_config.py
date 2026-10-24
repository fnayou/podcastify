#!/usr/bin/env python3
"""Tests for Config class."""

from pathlib import Path

from podcastify.config import Config


class TestConfigDefaults:
    def test_default_podcasts_root(self, monkeypatch):
        monkeypatch.delenv("PODCASTS_ROOT")
        assert Config.PODCASTS_ROOT == Path("/app/podcasts")

    def test_default_public_root(self, monkeypatch):
        monkeypatch.delenv("PUBLIC_ROOT")
        assert Config.PUBLIC_ROOT == Path("/app/public")

    def test_default_base_url(self):
        assert Config.BASE_URL == "http://localhost:8080"

    def test_default_publish_xml(self):
        assert Config.PUBLISH_XML is True

    def test_default_run_on_start(self):
        assert Config.RUN_ON_START is True


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

    def test_base_url_trailing_slash_stripped(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com/pods//")
        assert Config.BASE_URL == "https://example.com/pods"

    def test_base_url_whitespace_stripped(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_BASE_URL", "  https://example.com/ \n")
        assert Config.BASE_URL == "https://example.com"

    def test_publish_xml_false(self, monkeypatch):
        monkeypatch.setenv("PUBLISH_XML", "false")
        assert Config.PUBLISH_XML is False

    def test_publish_index_is_off_by_default(self, monkeypatch):
        monkeypatch.delenv("PUBLISH_INDEX", raising=False)
        assert Config.PUBLISH_INDEX is False

    def test_publish_index_true(self, monkeypatch):
        monkeypatch.setenv("PUBLISH_INDEX", "true")
        assert Config.PUBLISH_INDEX is True

    def test_run_on_start_false(self, monkeypatch):
        monkeypatch.setenv("RUN_ON_START", "false")
        assert Config.RUN_ON_START is False

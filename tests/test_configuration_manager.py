#!/usr/bin/env python3
"""Tests for ConfigurationManager class."""

from pathlib import Path

import yaml

from podcastify.config import Config
from podcastify.parser import ConfigurationManager


class TestLoadYaml:
    def test_load_valid_yaml(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text("name: test\ntitle: Test", encoding="utf-8")
        result = ConfigurationManager.load_yaml(f)
        assert result == {"name": "test", "title": "Test"}

    def test_load_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("", encoding="utf-8")
        result = ConfigurationManager.load_yaml(f)
        assert result == {}

    def test_load_invalid_yaml(self, tmp_path, capsys):
        f = tmp_path / "bad.yaml"
        f.write_text("{[", encoding="utf-8")
        result = ConfigurationManager.load_yaml(f)
        assert result == {}
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    def test_load_missing_file(self, capsys):
        result = ConfigurationManager.load_yaml(Path("/nonexistent/file.yaml"))
        assert result == {}
        captured = capsys.readouterr()
        assert "ERROR" in captured.out


class TestExtractPodcastMetadata:
    def test_flat_config(self, sample_flat_config):
        meta = ConfigurationManager.extract_podcast_metadata(sample_flat_config)
        assert meta["title"] == "My Show"
        assert meta["author-name"] == "Test Author"

    def test_nested_config(self, sample_nested_config):
        meta = ConfigurationManager.extract_podcast_metadata(sample_nested_config)
        assert meta["title"] == "Nested Show"
        assert meta["author-name"] == "Nested Author"

    def test_legacy_author_field(self, sample_legacy_config):
        meta = ConfigurationManager.extract_podcast_metadata(sample_legacy_config)
        assert meta["author-name"] == "Legacy Author"

    def test_missing_optional_fields(self):
        config = {"title": "Minimal"}
        meta = ConfigurationManager.extract_podcast_metadata(config)
        assert meta["title"] == "Minimal"
        assert "author-name" not in meta

    def test_partial_fields(self):
        config = {"title": "Partial", "author-name": "Author", "explicit": True}
        meta = ConfigurationManager.extract_podcast_metadata(config)
        assert meta["title"] == "Partial"
        assert meta["author-name"] == "Author"
        assert meta["explicit"] is True


class TestDiscoverPodcastConfigs:
    def test_finds_configs(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        (tmp_path / "myshow-podcast.yaml").write_text("name: myshow", encoding="utf-8")
        (tmp_path / "other-podcast.yml").write_text("name: other", encoding="utf-8")
        result = ConfigurationManager.discover_podcast_configs()
        names = [n for n, _ in result]
        assert "myshow" in names
        assert "other" in names

    def test_ignores_non_matching(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        (tmp_path / "readme.md").write_text("# Readme", encoding="utf-8")
        (tmp_path / "random.yaml").write_text("key: value", encoding="utf-8")
        result = ConfigurationManager.discover_podcast_configs()
        assert result == []

    def test_missing_directory(self, tmp_path, monkeypatch, capsys):
        missing = tmp_path / "missing"
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", missing)
        result = ConfigurationManager.discover_podcast_configs()
        assert result == []
        captured = capsys.readouterr()
        assert "WARN" in captured.out

    def test_skips_directories(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        (tmp_path / "subdir").mkdir()
        result = ConfigurationManager.discover_podcast_configs()
        assert result == []

    def test_sanitizes_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        # Create files that would derive names needing sanitization
        (tmp_path / "my..show-podcast.yaml").write_text("name: myshow", encoding="utf-8")
        (tmp_path / "other-podcast.yaml").write_text("name: other", encoding="utf-8")
        result = ConfigurationManager.discover_podcast_configs()
        names = [n for n, _ in result]
        assert "myshow" in names  # dots removed
        assert "other" in names

    def test_skips_empty_name_after_sanitize(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        (tmp_path / "..-podcast.yaml").write_text("name: empty", encoding="utf-8")
        result = ConfigurationManager.discover_podcast_configs()
        assert result == []
        captured = capsys.readouterr()
        assert "WARN" in captured.out

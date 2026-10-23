#!/usr/bin/env python3
"""Tests for ConfigurationManager class."""

from pathlib import Path

import pytest

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

    def test_load_invalid_yaml(self, tmp_path, caplog):
        import logging

        caplog.set_level(logging.DEBUG)
        f = tmp_path / "bad.yaml"
        f.write_text("{[", encoding="utf-8")
        result = ConfigurationManager.load_yaml(f)
        assert result == {}
        assert any(record.levelname == "ERROR" for record in caplog.records)

    def test_load_missing_file(self, caplog):
        import logging

        caplog.set_level(logging.DEBUG)
        result = ConfigurationManager.load_yaml(Path("/nonexistent/file.yaml"))
        assert result == {}
        assert any(record.levelname == "ERROR" for record in caplog.records)


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

    def test_missing_directory(self, tmp_path, monkeypatch, caplog):
        missing = tmp_path / "missing"
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", missing)
        result = ConfigurationManager.discover_podcast_configs()
        assert result == []
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_skips_directories(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        (tmp_path / "subdir").mkdir()
        result = ConfigurationManager.discover_podcast_configs()
        assert result == []

    @pytest.mark.parametrize(
        "filename",
        [
            "my..show-podcast.yaml",
            "..-podcast.yaml",
            "-podcast.yaml",
            "my show-podcast.yaml",
            "my#show-podcast.yaml",
            "my?show-podcast.yaml",
            "my%show-podcast.yaml",
            "café-podcast.yaml",
            "-lead-podcast.yaml",
        ],
    )
    def test_rejects_invalid_names(self, tmp_path, monkeypatch, caplog, filename):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        (tmp_path / filename).write_text("name: x", encoding="utf-8")
        (tmp_path / "other-podcast.yaml").write_text("name: other", encoding="utf-8")
        result = ConfigurationManager.discover_podcast_configs()
        assert [n for n, _ in result] == ["other"]
        assert any(filename in r.message and r.levelname in ("WARNING", "ERROR") for r in caplog.records)

    @pytest.mark.parametrize("name", ["myshow", "My_Show-2", "show.v2", "a", "9lives"])
    def test_accepts_valid_names(self, tmp_path, monkeypatch, name):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        (tmp_path / f"{name}-podcast.yaml").write_text("name: x", encoding="utf-8")
        result = ConfigurationManager.discover_podcast_configs()
        assert [n for n, _ in result] == [name]

    def test_rejects_second_config_for_same_name(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        (tmp_path / "myshow-podcast.yaml").write_text("name: one", encoding="utf-8")
        (tmp_path / "myshow-podcast.yml").write_text("name: two", encoding="utf-8")
        result = ConfigurationManager.discover_podcast_configs()
        assert result == [("myshow", tmp_path / "myshow-podcast.yaml")]
        errors = [r.message for r in caplog.records if r.levelname == "ERROR"]
        assert len(errors) == 1
        assert "myshow-podcast.yaml" in errors[0]
        assert "myshow-podcast.yml" in errors[0]

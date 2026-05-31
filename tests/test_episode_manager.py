#!/usr/bin/env python3
"""Tests for EpisodeManager class."""

from podcastify.config import Config
from podcastify.parser import EpisodeManager


class TestDiscoverEpisodes:
    def test_explicit_episodes(self, tmp_path, monkeypatch, sample_flat_config):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        episodes = EpisodeManager.discover_episodes("myshow", sample_flat_config)
        assert len(episodes) == 1
        assert episodes[0]["file"] == "ep01.mp3"
        assert "__resolved_path" in episodes[0]

    def test_auto_scan(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        (pub_dir / "ep02.mp3").write_bytes(b"\x00" * 64)
        episodes = EpisodeManager.discover_episodes("myshow", {})
        assert len(episodes) == 2
        assert episodes[0]["file"] == "ep01.mp3"
        assert episodes[1]["file"] == "ep02.mp3"

    def test_auto_scan_missing_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        episodes = EpisodeManager.discover_episodes("nonexistent", {})
        assert episodes == []

    def test_explicit_resolves_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "episode.mp3").write_bytes(b"\x00" * 64)
        cfg = {"episodes": [{"file": "episode.mp3"}]}
        episodes = EpisodeManager.discover_episodes("myshow", cfg)
        assert episodes[0]["__resolved_path"] == pub_dir / "episode.mp3"

    def test_explicit_uses_basename_only(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "episode.mp3").write_bytes(b"\x00" * 64)
        cfg = {"episodes": [{"file": "/some/path/episode.mp3"}]}
        episodes = EpisodeManager.discover_episodes("myshow", cfg)
        # original file value stays as-is; only __resolved_path uses basename
        assert episodes[0]["file"] == "/some/path/episode.mp3"
        assert episodes[0]["__resolved_path"] == pub_dir / "episode.mp3"


class TestResolveImageUrl:
    def test_local_file_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "cover.jpg").write_bytes(b"\x00" * 64)
        result = EpisodeManager.resolve_image_url("myshow", {"image": "cover.jpg"})
        assert result == "http://localhost:8080/myshow/cover.jpg"

    def test_local_file_missing(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        result = EpisodeManager.resolve_image_url("myshow", {"image": "missing.jpg"})
        assert result is None
        captured = capsys.readouterr()
        assert "WARN" in captured.out

    def test_absolute_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        result = EpisodeManager.resolve_image_url(
            "myshow", {"image": "https://example.com/cover.jpg"}
        )
        assert result == "https://example.com/cover.jpg"

    def test_no_image(self):
        result = EpisodeManager.resolve_image_url("myshow", {})
        assert result is None

    def test_http_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        result = EpisodeManager.resolve_image_url(
            "myshow", {"image": "http://example.com/cover.jpg"}
        )
        assert result == "http://example.com/cover.jpg"

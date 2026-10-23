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


class TestMediaUrl:
    def test_plain_name(self, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        assert EpisodeManager.media_url("myshow", "ep01.mp3") == "http://localhost:8080/myshow/ep01.mp3"

    def test_space_unicode_and_hash(self, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        result = EpisodeManager.media_url("myshow", "Épisode 1 #2.mp3")
        assert result == "http://localhost:8080/myshow/%C3%89pisode%201%20%232.mp3"

    def test_question_mark(self, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        assert EpisodeManager.media_url("myshow", "why?.mp3") == "http://localhost:8080/myshow/why%3F.mp3"

    def test_percent_sign(self, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        assert EpisodeManager.media_url("myshow", "100%.mp3") == "http://localhost:8080/myshow/100%25.mp3"

    def test_podcast_segment_encoded(self, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        assert EpisodeManager.media_url("my show", "a/b.mp3") == "http://localhost:8080/my%20show/a%2Fb.mp3"

    def test_trailing_slash_base_url(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://cdn.example.com/")
        assert EpisodeManager.media_url("myshow", "ep01.mp3") == "https://cdn.example.com/myshow/ep01.mp3"


class TestResolveImageUrl:
    def test_local_file_encoded(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setenv("PUBLIC_BASE_URL", " https://example.com/ ")
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "cover art #1.jpg").write_bytes(b"\x00" * 64)
        result = EpisodeManager.resolve_image_url("myshow", {"image": "cover art #1.jpg"})
        assert result == "https://example.com/myshow/cover%20art%20%231.jpg"

    def test_local_file_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "cover.jpg").write_bytes(b"\x00" * 64)
        result = EpisodeManager.resolve_image_url("myshow", {"image": "cover.jpg"})
        assert result == "http://localhost:8080/myshow/cover.jpg"

    def test_local_file_missing(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        result = EpisodeManager.resolve_image_url("myshow", {"image": "missing.jpg"})
        assert result is None
        assert any(record.levelname == "WARNING" for record in caplog.records)

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

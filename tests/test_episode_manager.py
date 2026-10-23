#!/usr/bin/env python3
"""Tests for EpisodeManager class."""

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from podcastify.parser import EpisodeManager, validate_podcast_config


def _validated(episodes):
    model, err = validate_podcast_config({"title": "T", "description": "D", "episodes": episodes})
    assert err is None
    return model


class TestDiscoverEpisodes:
    def test_empty_episode_list_falls_back_to_scan(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00")
        episodes = EpisodeManager.discover_episodes("myshow", _validated([]))
        assert [e["file"] for e in episodes] == ["ep01.mp3"]

    def test_explicit_list_wins_over_scan(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00")
        (pub_dir / "ep02.mp3").write_bytes(b"\x00")
        episodes = EpisodeManager.discover_episodes("myshow", _validated([{"file": "ep02.mp3"}]))
        assert [e["file"] for e in episodes] == ["ep02.mp3"]

    def test_explicit_episodes(self, tmp_path, monkeypatch, sample_flat_config):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        model, err = validate_podcast_config(sample_flat_config)
        assert err is None
        episodes = EpisodeManager.discover_episodes("myshow", model)
        assert len(episodes) == 1
        assert episodes[0]["file"] == "ep01.mp3"
        assert "__resolved_path" in episodes[0]

    def test_auto_scan(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        (pub_dir / "ep02.mp3").write_bytes(b"\x00" * 64)
        episodes = EpisodeManager.discover_episodes("myshow")
        assert len(episodes) == 2
        assert episodes[0]["file"] == "ep01.mp3"
        assert episodes[1]["file"] == "ep02.mp3"

    def test_auto_scan_missing_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        episodes = EpisodeManager.discover_episodes("nonexistent")
        assert episodes == []

    def test_explicit_resolves_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "episode.mp3").write_bytes(b"\x00" * 64)
        model = _validated([{"file": "episode.mp3"}])
        episodes = EpisodeManager.discover_episodes("myshow", model)
        assert episodes[0]["__resolved_path"] == pub_dir / "episode.mp3"

    def test_explicit_uses_basename_only(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "episode.mp3").write_bytes(b"\x00" * 64)
        model = _validated([{"file": "/some/path/episode.mp3"}])
        episodes = EpisodeManager.discover_episodes("myshow", model)
        # original file value stays as-is; only __resolved_path uses basename
        assert episodes[0]["file"] == "/some/path/episode.mp3"
        assert episodes[0]["__resolved_path"] == pub_dir / "episode.mp3"


class TestMediaScan:
    @pytest.mark.parametrize("name", ["a.mp3", "a.m4a", "a.mp4", "a.ogg", "a.opus", "EP01.MP3", "a.M4A"])
    def test_supported_extensions_are_found(self, tmp_path, monkeypatch, name):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / name).write_bytes(b"\x00")
        episodes = EpisodeManager.discover_episodes("myshow")
        assert [e["file"] for e in episodes] == [name]

    def test_other_files_and_directories_are_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "cover.jpg").write_bytes(b"\x00")
        (pub_dir / "notes.txt").write_bytes(b"\x00")
        (pub_dir / "folder.mp3").mkdir()
        (pub_dir / "ep.mp3").write_bytes(b"\x00")
        episodes = EpisodeManager.discover_episodes("myshow")
        assert [e["file"] for e in episodes] == ["ep.mp3"]

    def test_mixed_case_order_is_stable(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        for name in ("b.mp3", "A.MP3", "c.mp3"):
            (pub_dir / name).write_bytes(b"\x00")
        episodes = EpisodeManager.discover_episodes("myshow")
        assert [e["file"] for e in episodes] == ["A.MP3", "b.mp3", "c.mp3"]


class TestMediaType:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("a.mp3", "audio/mpeg"),
            ("a.MP3", "audio/mpeg"),
            ("a.m4a", "audio/x-m4a"),
            ("a.mp4", "video/mp4"),
            ("a.ogg", "audio/ogg"),
            ("a.opus", "audio/opus"),
            ("a.wav", "audio/mpeg"),
            ("noext", "audio/mpeg"),
        ],
    )
    def test_media_type(self, name, expected):
        assert EpisodeManager.media_type(Path(name)) == expected


class TestPublished:
    def test_pub_date_wins(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep.mp3").write_bytes(b"\x00")
        model = _validated([{"file": "ep.mp3", "pub_date": "2025-01-01T08:00:00"}])
        episodes = EpisodeManager.discover_episodes("myshow", model)
        assert episodes[0]["__published"] == datetime(2025, 1, 1, 8, tzinfo=timezone.utc)

    def test_mtime_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        mp3 = pub_dir / "ep.mp3"
        mp3.write_bytes(b"\x00")
        os.utime(mp3, (1700000000, 1700000000))
        model = _validated([{"file": "ep.mp3"}])
        episodes = EpisodeManager.discover_episodes("myshow", model)
        assert episodes[0]["__published"] == datetime.fromtimestamp(1700000000, tz=timezone.utc)

    def test_auto_scan_uses_mtime(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        mp3 = pub_dir / "ep.mp3"
        mp3.write_bytes(b"\x00")
        os.utime(mp3, (1700000000, 1700000000))
        episodes = EpisodeManager.discover_episodes("myshow")
        assert episodes[0]["__published"] == datetime.fromtimestamp(1700000000, tz=timezone.utc)

    def test_missing_file_falls_back_to_epoch(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        (tmp_path / "myshow").mkdir()
        model = _validated([{"file": "gone.mp3"}])
        episodes = EpisodeManager.discover_episodes("myshow", model)
        assert episodes[0]["__published"] == datetime.fromtimestamp(0, tz=timezone.utc)


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
        warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert warnings == [f"Image file not found: {pub_dir / 'missing.jpg'}"]

    def test_absolute_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        result = EpisodeManager.resolve_image_url("myshow", {"image": "https://example.com/cover.jpg"})
        assert result == "https://example.com/cover.jpg"

    def test_no_image(self):
        result = EpisodeManager.resolve_image_url("myshow", {})
        assert result is None

    def test_http_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        result = EpisodeManager.resolve_image_url("myshow", {"image": "http://example.com/cover.jpg"})
        assert result == "http://example.com/cover.jpg"

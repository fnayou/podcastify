#!/usr/bin/env python3
"""Tests for MediaProcessor class."""

import subprocess
from pathlib import Path

import pytest

from podcastify.media import MediaProcessor


class TestFormatItunesDuration:
    def test_none_returns_none(self):
        assert MediaProcessor.format_itunes_duration(None) is None

    def test_zero_seconds(self):
        assert MediaProcessor.format_itunes_duration(0) == "0:00"

    def test_under_one_minute(self):
        assert MediaProcessor.format_itunes_duration(45) == "0:45"

    def test_exactly_one_minute(self):
        assert MediaProcessor.format_itunes_duration(60) == "1:00"

    def test_under_one_hour(self):
        assert MediaProcessor.format_itunes_duration(1845) == "30:45"

    def test_exactly_one_hour(self):
        assert MediaProcessor.format_itunes_duration(3600) == "1:00:00"

    def test_over_one_hour(self):
        assert MediaProcessor.format_itunes_duration(7265) == "2:01:05"

    def test_fractional_seconds_rounded(self):
        assert MediaProcessor.format_itunes_duration(30.4) == "0:30"
        assert MediaProcessor.format_itunes_duration(30.6) == "0:31"

    def test_negative_seconds_clamped(self):
        assert MediaProcessor.format_itunes_duration(-5) == "0:00"


class TestGetDurationSeconds:
    def test_missing_file_returns_none(self):
        result = MediaProcessor.get_duration_seconds(Path("/nonexistent/file.mp3"))
        assert result is None

    def test_success(self, mocker, mock_mp3):
        proc_mock = mocker.patch(
            "podcastify.media.subprocess.run",
            return_value=mocker.Mock(stdout="1845.2\n", stderr=""),
        )
        result = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result == 1845.2
        proc_mock.assert_called_once()
        args = proc_mock.call_args[0][0]
        assert args[0] == "ffprobe"
        assert "format=duration" in args

    def test_called_process_error(self, mocker, mock_mp3):
        mocker.patch(
            "podcastify.media.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "ffprobe"),
        )
        result = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result is None

    def test_timeout(self, mocker, mock_mp3):
        mocker.patch(
            "podcastify.media.subprocess.run",
            side_effect=subprocess.TimeoutExpired("ffprobe", 30),
        )
        result = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result is None

    def test_value_error(self, mocker, mock_mp3):
        mocker.patch(
            "podcastify.media.subprocess.run",
            return_value=mocker.Mock(stdout="not-a-number", stderr=""),
        )
        result = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result is None

    def test_cache_hit(self, mocker, mock_mp3):
        MediaProcessor.clear_cache()
        proc_mock = mocker.patch(
            "podcastify.media.subprocess.run",
            return_value=mocker.Mock(stdout="1234.5\n", stderr=""),
        )
        # First call should invoke ffprobe
        result1 = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result1 == 1234.5
        assert proc_mock.call_count == 1
        # Second call should hit cache (no additional ffprobe call)
        result2 = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result2 == 1234.5
        assert proc_mock.call_count == 1

    def test_cache_miss_on_mtime_change(self, mocker, mock_mp3):
        MediaProcessor.clear_cache()
        proc_mock = mocker.patch(
            "podcastify.media.subprocess.run",
            side_effect=[
                mocker.Mock(stdout="1000.0\n", stderr=""),
                mocker.Mock(stdout="2000.0\n", stderr=""),
            ],
        )
        result1 = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result1 == 1000.0
        # Modify the file to change mtime
        mock_mp3.write_bytes(b"\x00" * 2048)
        result2 = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result2 == 2000.0
        assert proc_mock.call_count == 2

    def test_failure_cached(self, mocker, mock_mp3):
        MediaProcessor.clear_cache()
        mocker.patch(
            "podcastify.media.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "ffprobe"),
        )
        result1 = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result1 is None
        # Second call should also return None from cache
        result2 = MediaProcessor.get_duration_seconds(mock_mp3)
        assert result2 is None

    def test_disk_cache_persists(self, mocker, mock_mp3, tmp_path, monkeypatch):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        monkeypatch.setattr("podcastify.config.Config.CACHE_ROOT", cache_root)
        MediaProcessor.clear_cache()
        proc_mock = mocker.patch(
            "podcastify.media.subprocess.run",
            return_value=mocker.Mock(stdout="999.0\n", stderr=""),
        )
        assert MediaProcessor.get_duration_seconds(mock_mp3) == 999.0
        assert proc_mock.call_count == 1
        MediaProcessor._duration_cache.clear()
        MediaProcessor._disk_loaded = False
        proc_mock.reset_mock()
        assert MediaProcessor.get_duration_seconds(mock_mp3) == 999.0
        proc_mock.assert_not_called()

    def test_legacy_cache_migration(self, mocker, mock_mp3, tmp_path, monkeypatch):
        public_root = tmp_path / "public"
        cache_root = tmp_path / "cache"
        public_root.mkdir()
        public_root.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public_root)
        monkeypatch.setattr("podcastify.config.Config.CACHE_ROOT", cache_root)

        legacy_cache = public_root / ".podcastify-cache.json"
        legacy_cache.write_text('{"path|123.45": 567.89}', encoding="utf-8")

        MediaProcessor.clear_cache()
        proc_mock = mocker.patch(
            "podcastify.media.subprocess.run",
            return_value=mocker.Mock(stdout="100.0\n", stderr=""),
        )

        MediaProcessor._load_disk_cache()

        assert not legacy_cache.exists()
        new_cache = cache_root / ".podcastify-cache.json"
        assert new_cache.exists()
        assert "path|123.45" in new_cache.read_text(encoding="utf-8")

    def test_cache_pruning_removes_nonexistent_files(self, mocker, tmp_path, monkeypatch):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        monkeypatch.setattr("podcastify.config.Config.CACHE_ROOT", cache_root)

        MediaProcessor.clear_cache()

        existing_file = tmp_path / "exists.mp3"
        existing_file.write_bytes(b"\x00" * 1024)
        nonexistent_file = tmp_path / "missing.mp3"

        key_exists = (str(existing_file), 123.45)
        key_missing = (str(nonexistent_file), 456.78)

        MediaProcessor._duration_cache[key_exists] = 100.0
        MediaProcessor._duration_cache[key_missing] = 200.0

        MediaProcessor._save_disk_cache()

        cache_content = cache_root / ".podcastify-cache.json"
        content = cache_content.read_text(encoding="utf-8")

        assert str(existing_file) in content
        assert str(nonexistent_file) not in content

    def test_warm_durations_parallel(self, mocker, tmp_path):
        MediaProcessor.clear_cache()
        paths = []
        for i in range(3):
            p = tmp_path / f"ep{i}.mp3"
            p.write_bytes(b"\x00" * 64)
            paths.append(p)
        proc_mock = mocker.patch(
            "podcastify.media.subprocess.run",
            return_value=mocker.Mock(stdout="60.0\n", stderr=""),
        )
        MediaProcessor.warm_durations_parallel(paths, max_workers=2)
        assert proc_mock.call_count == 3

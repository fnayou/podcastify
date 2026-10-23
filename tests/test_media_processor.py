#!/usr/bin/env python3
"""Tests for MediaProcessor class."""

import json
import logging
import os
import random
from pathlib import Path

import pytest
from tinytag import TinyTag, TinyTagException

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


def _warnings(caplog):
    return [r.message for r in caplog.records if r.levelname == "WARNING"]


def _restart_process():
    MediaProcessor._duration_cache.clear()
    MediaProcessor._disk_loaded = False


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    monkeypatch.setattr("podcastify.config.Config.CACHE_ROOT", cache_root)
    MediaProcessor.clear_cache()
    return cache_root / ".podcastify-cache.json"


@pytest.fixture
def tag_reads(mocker):
    return mocker.spy(TinyTag, "get")


class TestDurationPerFormat:
    @pytest.mark.parametrize(
        "name",
        [
            "cbr.mp3",
            "cbr-noxing.mp3",
            "vbr-xing.mp3",
            "id3-cover.mp3",
            "tone.m4a",
            "tone.mp4",
            "tone.ogg",
            "tone.opus",
        ],
    )
    def test_reads_the_encoded_length(self, audio_fixture, name):
        assert MediaProcessor.get_duration_seconds(audio_fixture(name)) == pytest.approx(1.0, abs=0.1)

    def test_truncated_file_with_xing_header_reports_the_full_length(self, audio_fixture):
        assert MediaProcessor.get_duration_seconds(audio_fixture("truncated.mp3")) == pytest.approx(1.0, abs=0.1)


class TestGuards:
    def test_missing_file_returns_none(self):
        assert MediaProcessor.get_duration_seconds(Path("/nonexistent/file.mp3")) is None

    def test_zero_byte_file_returns_none(self, audio_fixture, caplog):
        assert MediaProcessor.get_duration_seconds(audio_fixture("zero-byte.mp3")) is None
        assert _warnings(caplog) == ["Failed to get duration for zero-byte.mp3: <zero-byte file>"]

    def test_small_garbage_file_returns_none(self, audio_fixture):
        assert MediaProcessor.get_duration_seconds(audio_fixture("garbage.mp3")) is None

    def test_large_garbage_file_that_parses_as_a_short_frame_returns_none(self, tmp_path, caplog):
        rng = random.Random(46)
        garbage = tmp_path / "garbage.mp3"
        garbage.write_bytes(bytes(rng.getrandbits(8) for _ in range(200000)))
        assert TinyTag.get(str(garbage)).duration < 1.0
        assert MediaProcessor.get_duration_seconds(garbage) is None
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert warnings[0].startswith("Failed to get duration for garbage.mp3: <implausible duration 0.0")

    def test_short_duration_is_kept_for_a_small_file(self, mocker, mock_mp3):
        mocker.patch("podcastify.media.TinyTag.get", return_value=mocker.Mock(duration=0.5))
        assert MediaProcessor.get_duration_seconds(mock_mp3) == 0.5

    def test_one_second_is_kept_for_a_large_file(self, mocker, tmp_path):
        big = tmp_path / "big.mp3"
        big.write_bytes(b"\x00" * 100 * 1024)
        mocker.patch("podcastify.media.TinyTag.get", return_value=mocker.Mock(duration=1.0))
        assert MediaProcessor.get_duration_seconds(big) == 1.0

    def test_short_duration_is_rejected_at_the_size_threshold(self, mocker, tmp_path):
        big = tmp_path / "big.mp3"
        big.write_bytes(b"\x00" * 100 * 1024)
        mocker.patch("podcastify.media.TinyTag.get", return_value=mocker.Mock(duration=0.99))
        assert MediaProcessor.get_duration_seconds(big) is None

    @pytest.mark.parametrize("value", [None, 0, 0.0, -3.5, float("nan"), float("inf"), float("-inf")])
    def test_unusable_duration_returns_none(self, mocker, mock_mp3, caplog, value):
        mocker.patch("podcastify.media.TinyTag.get", return_value=mocker.Mock(duration=value))
        assert MediaProcessor.get_duration_seconds(mock_mp3) is None
        assert len(_warnings(caplog)) == 1


class TestReadErrors:
    @pytest.mark.parametrize(
        "error, message",
        [
            (TinyTagException("File is not a supported format"), "File is not a supported format"),
            (OSError("Input/output error"), "Input/output error"),
            (ValueError(), "ValueError"),
        ],
    )
    def test_exception_returns_none_and_logs_the_message(self, mocker, mock_mp3, caplog, error, message):
        mocker.patch("podcastify.media.TinyTag.get", side_effect=error)
        assert MediaProcessor.get_duration_seconds(mock_mp3) is None
        assert _warnings(caplog) == [f"Failed to get duration for dummy.mp3: {message}"]

    def test_failure_is_warned_once_per_file(self, mocker, mock_mp3, caplog):
        get = mocker.patch("podcastify.media.TinyTag.get", side_effect=TinyTagException("bad"))
        assert MediaProcessor.get_duration_seconds(mock_mp3) is None
        assert MediaProcessor.get_duration_seconds(mock_mp3) is None
        assert get.call_count == 1
        assert len(_warnings(caplog)) == 1

    def test_unsupported_extension_returns_none(self, tmp_path, caplog):
        notes = tmp_path / "notes.txt"
        notes.write_text("not audio", encoding="utf-8")
        assert MediaProcessor.get_duration_seconds(notes) is None
        assert len(_warnings(caplog)) == 1


class TestCache:
    def test_cache_hit_skips_the_read(self, audio_fixture, tag_reads):
        path = audio_fixture("cbr.mp3")
        first = MediaProcessor.get_duration_seconds(path)
        second = MediaProcessor.get_duration_seconds(path)
        assert first == second
        assert tag_reads.call_count == 1

    def test_cache_miss_on_mtime_change(self, audio_fixture, tag_reads):
        path = audio_fixture("cbr.mp3")
        MediaProcessor.get_duration_seconds(path)
        stat = path.stat()
        os.utime(path, (stat.st_atime, stat.st_mtime + 10))
        MediaProcessor.get_duration_seconds(path)
        assert tag_reads.call_count == 2

    def test_failure_is_cached(self, audio_fixture, tag_reads):
        path = audio_fixture("garbage.mp3")
        assert MediaProcessor.get_duration_seconds(path) is None
        assert MediaProcessor.get_duration_seconds(path) is None
        assert tag_reads.call_count == 1

    def test_failure_is_persisted(self, audio_fixture, cache_file):
        path = audio_fixture("garbage.mp3")
        MediaProcessor.get_duration_seconds(path)
        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        assert list(saved["durations"].values()) == [None]

    def test_disk_cache_persists(self, audio_fixture, cache_file, tag_reads):
        path = audio_fixture("cbr.mp3")
        duration = MediaProcessor.get_duration_seconds(path)
        _restart_process()
        tag_reads.reset_mock()
        assert MediaProcessor.get_duration_seconds(path) == duration
        tag_reads.assert_not_called()

    def test_persist_false_keeps_the_disk_cache_untouched(self, audio_fixture, cache_file):
        MediaProcessor.get_duration_seconds(audio_fixture("cbr.mp3"), persist=False)
        assert not cache_file.exists()

    def test_save_writes_the_format_version(self, audio_fixture, cache_file):
        MediaProcessor.get_duration_seconds(audio_fixture("cbr.mp3"))
        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        assert saved["version"] == MediaProcessor.CACHE_VERSION
        assert len(saved["durations"]) == 1

    def test_cache_version_was_bumped(self):
        assert MediaProcessor.CACHE_VERSION >= 2

    def test_old_format_entries_are_ignored_and_files_are_read_again(self, audio_fixture, cache_file, tag_reads):
        path = audio_fixture("cbr.mp3")
        old_entry = {f"{path}|{path.stat().st_mtime}": 9999.0}
        cache_file.write_text(json.dumps(old_entry), encoding="utf-8")
        assert MediaProcessor.get_duration_seconds(path) == pytest.approx(1.0, abs=0.1)
        assert tag_reads.call_count == 1
        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        assert saved["version"] == MediaProcessor.CACHE_VERSION
        assert 9999.0 not in saved["durations"].values()

    def test_entries_from_another_version_are_ignored(self, audio_fixture, cache_file, tag_reads):
        path = audio_fixture("cbr.mp3")
        stale = {"version": MediaProcessor.CACHE_VERSION + 1, "durations": {f"{path}|{path.stat().st_mtime}": 9999.0}}
        cache_file.write_text(json.dumps(stale), encoding="utf-8")
        assert MediaProcessor.get_duration_seconds(path) == pytest.approx(1.0, abs=0.1)
        assert tag_reads.call_count == 1

    def test_current_version_entries_are_used(self, audio_fixture, cache_file, tag_reads):
        path = audio_fixture("cbr.mp3")
        current = {"version": MediaProcessor.CACHE_VERSION, "durations": {f"{path}|{path.stat().st_mtime}": 123.0}}
        cache_file.write_text(json.dumps(current), encoding="utf-8")
        assert MediaProcessor.get_duration_seconds(path) == 123.0
        tag_reads.assert_not_called()

    def test_legacy_cache_migration(self, tmp_path, monkeypatch, cache_file):
        public_root = tmp_path / "public"
        public_root.mkdir()
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public_root)
        legacy_cache = public_root / ".podcastify-cache.json"
        legacy_cache.write_text('{"path|123.45": 567.89}', encoding="utf-8")

        MediaProcessor._load_disk_cache()

        assert not legacy_cache.exists()
        assert "path|123.45" in cache_file.read_text(encoding="utf-8")
        assert MediaProcessor._duration_cache == {}

    def test_migrated_legacy_cache_is_replaced_by_the_new_format(
        self, audio_fixture, tmp_path, monkeypatch, cache_file
    ):
        public_root = tmp_path / "public"
        public_root.mkdir()
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public_root)
        path = audio_fixture("cbr.mp3")
        legacy = public_root / ".podcastify-cache.json"
        legacy.write_text(json.dumps({f"{path}|{path.stat().st_mtime}": 9999.0}), encoding="utf-8")

        assert MediaProcessor.get_duration_seconds(path) == pytest.approx(1.0, abs=0.1)

        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        assert saved["version"] == MediaProcessor.CACHE_VERSION
        assert list(saved["durations"].values()) != [9999.0]

    def test_cache_pruning_removes_nonexistent_files(self, tmp_path, cache_file):
        existing_file = tmp_path / "exists.mp3"
        existing_file.write_bytes(b"\x00" * 1024)
        nonexistent_file = tmp_path / "missing.mp3"
        MediaProcessor._duration_cache[(str(existing_file), 123.45)] = 100.0
        MediaProcessor._duration_cache[(str(nonexistent_file), 456.78)] = 200.0

        MediaProcessor._save_disk_cache()

        content = cache_file.read_text(encoding="utf-8")
        assert str(existing_file) in content
        assert str(nonexistent_file) not in content

    def test_save_keeps_newest_mtime_per_path(self, mock_mp3, cache_file):
        path = str(mock_mp3)
        MediaProcessor._duration_cache[(path, 100.0)] = 1.0
        MediaProcessor._duration_cache[(path, 300.0)] = 3.0
        MediaProcessor._duration_cache[(path, 200.0)] = 2.0
        MediaProcessor._save_disk_cache()
        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        assert saved["durations"] == {f"{path}|300.0": 3.0}

    @pytest.mark.parametrize("content", ['["a"]', '"text"', "42"])
    def test_non_dict_cache_is_ignored(self, cache_file, content):
        cache_file.write_text(content, encoding="utf-8")
        MediaProcessor._load_disk_cache()
        assert MediaProcessor._duration_cache == {}

    @pytest.mark.parametrize("durations", [["a"], "text", 42, None])
    def test_non_dict_durations_are_ignored(self, cache_file, durations):
        payload = {"version": MediaProcessor.CACHE_VERSION, "durations": durations}
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        MediaProcessor._load_disk_cache()
        assert MediaProcessor._duration_cache == {}

    def test_malformed_keys_are_skipped_and_good_keys_kept(self, cache_file):
        durations = {"no-separator": 1.0, "/a.mp3|not-a-float": 2.0, "/b.mp3|5.5": 3.0}
        payload = {"version": MediaProcessor.CACHE_VERSION, "durations": durations}
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        MediaProcessor._load_disk_cache()
        assert MediaProcessor._duration_cache == {("/b.mp3", 5.5): 3.0}

    def test_corrupt_cache_warns_with_reason(self, cache_file, caplog):
        cache_file.write_text("{not json", encoding="utf-8")
        MediaProcessor._load_disk_cache()
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert warnings[0].startswith("Failed to load duration cache: ")
        assert MediaProcessor._duration_cache == {}

    def test_corrupt_legacy_cache_warns_and_is_kept(self, tmp_path, monkeypatch, cache_file, caplog):
        public_root = tmp_path / "public"
        public_root.mkdir()
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public_root)
        legacy = public_root / ".podcastify-cache.json"
        legacy.write_text("{not json", encoding="utf-8")
        MediaProcessor._load_disk_cache()
        assert _warnings(caplog)[0].startswith("Failed to migrate legacy cache: ")
        assert legacy.exists()
        assert not cache_file.exists()

    def test_non_dict_legacy_cache_is_not_migrated(self, tmp_path, monkeypatch, cache_file):
        public_root = tmp_path / "public"
        public_root.mkdir()
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public_root)
        legacy = public_root / ".podcastify-cache.json"
        legacy.write_text("[1, 2]", encoding="utf-8")
        MediaProcessor._load_disk_cache()
        assert legacy.exists()
        assert not cache_file.exists()

    def test_clear_cache_removes_the_cache_file(self, cache_file):
        cache_file.write_text("{}", encoding="utf-8")
        MediaProcessor.clear_cache()
        assert not cache_file.exists()

    def test_unwritable_cache_warns_with_reason(self, mocker, mock_mp3, cache_file, caplog):
        MediaProcessor._duration_cache[(str(mock_mp3), 1.0)] = 2.0
        mocker.patch("pathlib.Path.write_text", side_effect=OSError("disk full"))
        MediaProcessor._save_disk_cache()
        assert _warnings(caplog) == ["Failed to save duration cache: disk full"]


class TestStatFailures:
    def test_stat_failure_after_exists_returns_none(self, mocker):
        fake = mocker.Mock(spec=Path)
        fake.exists.return_value = True
        fake.stat.side_effect = OSError("gone")
        assert MediaProcessor.get_duration_seconds(fake) is None

    def test_size_check_failure_is_logged_and_cached(self, mocker, caplog):
        fake = mocker.Mock(spec=Path)
        fake.name = "a.mp3"
        fake.exists.return_value = True
        fake.stat.side_effect = [mocker.Mock(st_mtime=1.0), OSError("gone")]
        assert MediaProcessor.get_duration_seconds(fake, persist=False) is None
        assert _warnings(caplog) == ["Failed to get duration for a.mp3: <size check failed>"]
        assert MediaProcessor._duration_cache[(str(fake), 1.0)] is None


class TestWarmDurations:
    def test_skips_missing_files(self, tmp_path, tag_reads):
        MediaProcessor.warm_durations([tmp_path / "missing.mp3"])
        tag_reads.assert_not_called()

    def test_skips_files_whose_stat_fails(self, mocker, tag_reads):
        fake = mocker.Mock(spec=Path)
        fake.exists.return_value = True
        fake.stat.side_effect = OSError("gone")
        MediaProcessor.warm_durations([fake])
        tag_reads.assert_not_called()

    def test_skips_files_already_cached(self, mock_mp3, tag_reads):
        MediaProcessor._duration_cache[(str(mock_mp3), mock_mp3.stat().st_mtime)] = 12.0
        MediaProcessor.warm_durations([mock_mp3])
        tag_reads.assert_not_called()

    def test_reads_uncached_files_once_each_and_saves_once(self, mocker, audio_fixture, cache_file, tag_reads):
        paths = [audio_fixture(name) for name in ("cbr.mp3", "tone.m4a", "tone.ogg")]
        save = mocker.spy(MediaProcessor, "_save_disk_cache")
        MediaProcessor.warm_durations(paths)
        assert tag_reads.call_count == 3
        assert save.call_count == 1
        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        assert len(saved["durations"]) == 3

    def test_a_failing_file_does_not_stop_the_others(self, audio_fixture, caplog):
        paths = [audio_fixture("garbage.mp3"), audio_fixture("cbr.mp3")]
        caplog.set_level(logging.WARNING)
        MediaProcessor.warm_durations(paths)
        assert MediaProcessor._duration_cache[(str(paths[0]), paths[0].stat().st_mtime)] is None
        assert MediaProcessor._duration_cache[(str(paths[1]), paths[1].stat().st_mtime)] == pytest.approx(1.0, abs=0.1)

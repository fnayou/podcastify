#!/usr/bin/env python3
"""Tests for FeedWatcher class."""

import os
from pathlib import Path

import pytest

from podcastify.cli import FeedWatcher, main

CONFIG = b"title: My Show\ndescription: D\n"


class StopLoop(Exception):
    pass


@pytest.fixture
def roots(tmp_path, monkeypatch):
    podcasts = tmp_path / "podcasts"
    public = tmp_path / "public"
    podcasts.mkdir()
    public.mkdir()
    monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", podcasts)
    monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public)
    monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
    (podcasts / "myshow-podcast.yaml").write_bytes(CONFIG)
    (public / "myshow").mkdir()
    (public / "myshow" / "ep01.mp3").write_bytes(b"\x00" * 64)
    return podcasts, public


@pytest.fixture
def processor(mocker):
    proc = mocker.Mock()
    proc.process_all_podcasts.return_value = 0
    return proc


class TestFingerprint:
    def test_stable_without_changes(self, roots):
        assert FeedWatcher.fingerprint() == FeedWatcher.fingerprint()

    def test_new_media_changes_it(self, roots):
        _, public = roots
        before = FeedWatcher.fingerprint()
        (public / "myshow" / "ep02.mp3").write_bytes(b"\x00" * 64)
        assert FeedWatcher.fingerprint() != before

    def test_config_edit_changes_it(self, roots):
        podcasts, _ = roots
        before = FeedWatcher.fingerprint()
        (podcasts / "myshow-podcast.yaml").write_bytes(CONFIG + b"language: fr\n")
        assert FeedWatcher.fingerprint() != before

    def test_media_mtime_changes_it(self, roots):
        _, public = roots
        before = FeedWatcher.fingerprint()
        os.utime(public / "myshow" / "ep01.mp3", (0, 0))
        assert FeedWatcher.fingerprint() != before

    def test_ignores_generated_feeds_and_other_files(self, roots):
        podcasts, public = roots
        before = FeedWatcher.fingerprint()
        (public / "myshow.xml").write_text("<rss/>", encoding="utf-8")
        (public / ".myshow.abc.xml.tmp").write_text("x", encoding="utf-8")
        (public / "myshow" / "cover.jpg").write_bytes(b"\x00")
        (podcasts / "notes.txt").write_text("x", encoding="utf-8")
        assert FeedWatcher.fingerprint() == before

    def test_missing_roots_give_empty_fingerprint(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path / "none")
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path / "none")
        assert FeedWatcher.fingerprint() == ()

    def test_file_vanishing_mid_scan_is_skipped(self, roots, mocker):
        real_stat = Path.stat

        def stat(path, **kwargs):
            if path.name == "ep01.mp3":
                raise FileNotFoundError("gone")
            return real_stat(path, **kwargs)

        mocker.patch.object(Path, "stat", autospec=True, side_effect=stat)
        assert [Path(entry[0]).name for entry in FeedWatcher.fingerprint()] == ["myshow-podcast.yaml"]


class TestCheck:
    def test_no_change_does_not_regenerate(self, roots, processor):
        watcher = FeedWatcher(processor, interval=5)
        assert watcher.check() is None
        processor.process_all_podcasts.assert_not_called()

    def test_change_regenerates_once(self, roots, processor):
        _, public = roots
        watcher = FeedWatcher(processor, interval=5)
        (public / "myshow" / "ep02.mp3").write_bytes(b"\x00" * 64)
        assert watcher.check() == 0
        assert watcher.check() is None
        processor.process_all_podcasts.assert_called_once()

    def test_initial_run_regenerates_on_first_check(self, roots, processor):
        watcher = FeedWatcher(processor, interval=5, initial_run=True)
        assert watcher.check() == 0
        processor.process_all_podcasts.assert_called_once()

    def test_failure_is_logged_and_waits_for_the_next_change(self, roots, processor, caplog):
        processor.process_all_podcasts.return_value = 1
        watcher = FeedWatcher(processor, interval=5, initial_run=True)
        assert watcher.check() == 1
        assert watcher.check() is None
        record = next(r for r in caplog.records if "1 podcast(s) failed" in r.message)
        assert record.levelname == "ERROR"


class TestRun:
    def test_sleeps_the_interval_between_checks(self, roots, processor, mocker):
        sleep = mocker.patch("podcastify.cli.time.sleep", side_effect=[None, StopLoop])
        watcher = FeedWatcher(processor, interval=7)
        check = mocker.spy(watcher, "check")
        with pytest.raises(StopLoop):
            watcher.run()
        assert [c.args for c in sleep.call_args_list] == [(7,), (7,)]
        assert check.call_count == 1


class TestWatchCommand:
    def test_watch_runs_the_watcher(self, roots, mocker):
        run = mocker.patch("podcastify.cli.FeedWatcher.run")
        init = mocker.spy(FeedWatcher, "__init__")
        assert main(["watch", "--interval", "30"]) == 0
        run.assert_called_once()
        assert init.call_args.kwargs == {"interval": 30, "initial_run": False}

    def test_initial_run_flag(self, roots, mocker):
        mocker.patch("podcastify.cli.FeedWatcher.run")
        init = mocker.spy(FeedWatcher, "__init__")
        assert main(["watch", "--interval", "30", "--initial-run"]) == 0
        assert init.call_args.kwargs["initial_run"] is True

    def test_does_not_generate_at_start(self, roots, mocker):
        mocker.patch("podcastify.cli.FeedWatcher.run")
        _, public = roots
        main(["watch", "--interval", "30"])
        assert not (public / "myshow.xml").exists()

    @pytest.mark.parametrize("argv", [["watch"], ["watch", "--interval", "0"], ["watch", "--interval", "x"]])
    def test_interval_must_be_a_positive_integer(self, argv, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 2
        assert "usage:" in capsys.readouterr().err

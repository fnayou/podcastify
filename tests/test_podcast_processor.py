#!/usr/bin/env python3
"""Tests for PodcastProcessor class."""

import os
import time
from datetime import datetime, timezone

import yaml

from podcastify.cli import PodcastProcessor


class TestProcessPodcast:
    def test_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        # config
        cfg = tmp_path / "myshow-podcast.yaml"
        cfg.write_text(
            yaml.safe_dump(
                {
                    "title": "My Show",
                    "author-name": "Author",
                    "description": "Desc",
                    "episodes": [{"file": "ep01.mp3", "title": "Episode 1"}],
                }
            ),
            encoding="utf-8",
        )
        # media
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        proc = PodcastProcessor()
        ok = proc.process_podcast("myshow", cfg)
        assert ok is True
        assert (tmp_path / "myshow.xml").exists()

    def test_empty_config(self, tmp_path, caplog):
        cfg = tmp_path / "empty-podcast.yaml"
        cfg.write_text("", encoding="utf-8")
        proc = PodcastProcessor()
        ok = proc.process_podcast("empty", cfg)
        assert ok is False
        errors = [r.message for r in caplog.records if r.levelname == "ERROR"]
        assert "Empty or invalid config for empty" in errors

    def test_unexpected_error_logs_traceback(self, tmp_path, monkeypatch, caplog, mocker):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        cfg = tmp_path / "myshow-podcast.yaml"
        cfg.write_text(
            yaml.safe_dump({"title": "T", "description": "D", "episodes": [{"file": "ep01.mp3"}]}),
            encoding="utf-8",
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        mocker.patch("podcastify.cli.RSSGenerator.generate_feed_xml", side_effect=TypeError("boom"))
        ok = PodcastProcessor().process_podcast("myshow", cfg)
        assert ok is False
        record = next(r for r in caplog.records if "Failed to process myshow" in r.message)
        assert record.levelname == "ERROR"
        assert record.exc_info[0] is TypeError
        assert not (tmp_path / "myshow.xml").exists()

    def test_validation_failure(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        cfg = tmp_path / "bad-podcast.yaml"
        cfg.write_text(
            yaml.safe_dump({"title": "Missing Description"}),
            encoding="utf-8",
        )
        pub = tmp_path / "bad"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        proc = PodcastProcessor()
        ok = proc.process_podcast("bad", cfg)
        assert ok is False
        errors = [r.message for r in caplog.records if r.levelname == "ERROR"]
        assert len(errors) == 1
        assert errors[0].startswith("Config validation failed for bad:")

    def test_bad_base_url_scheme(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setenv("PUBLIC_BASE_URL", "ftp://example.com")
        cfg = tmp_path / "myshow-podcast.yaml"
        cfg.write_text(
            yaml.safe_dump(
                {
                    "title": "My Show",
                    "author-name": "Author",
                    "description": "Desc",
                    "episodes": [{"file": "ep01.mp3"}],
                }
            ),
            encoding="utf-8",
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        proc = PodcastProcessor()
        ok = proc.process_podcast("myshow", cfg)
        assert ok is False
        assert not (tmp_path / "myshow.xml").exists()
        assert any(
            record.levelname == "ERROR"
            and "PUBLIC_BASE_URL" in record.message
            and "ftp://example.com" in record.message
            for record in caplog.records
        )

    def test_missing_public_dir(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        cfg = tmp_path / "myshow-podcast.yaml"
        cfg.write_text(
            yaml.safe_dump({"title": "My Show", "author-name": "Author", "description": "Desc"}),
            encoding="utf-8",
        )
        proc = PodcastProcessor()
        ok = proc.process_podcast("myshow", cfg)
        assert ok is False
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_no_episodes(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        cfg = tmp_path / "myshow-podcast.yaml"
        cfg.write_text(
            yaml.safe_dump(
                {
                    "title": "My Show",
                    "author-name": "Author",
                    "description": "Desc",
                    "episodes": [],
                }
            ),
            encoding="utf-8",
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        proc = PodcastProcessor()
        ok = proc.process_podcast("myshow", cfg)
        assert ok is False
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_name_mismatch(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        cfg = tmp_path / "myshow-podcast.yaml"
        cfg.write_text(
            yaml.safe_dump(
                {
                    "name": "different",
                    "title": "My Show",
                    "author-name": "Author",
                    "description": "Desc",
                    "episodes": [{"file": "ep01.mp3"}],
                }
            ),
            encoding="utf-8",
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        proc = PodcastProcessor()
        ok = proc.process_podcast("myshow", cfg)
        assert ok is True
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_publish_xml_false(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", False)
        cfg = tmp_path / "myshow-podcast.yaml"
        cfg.write_text(
            yaml.safe_dump(
                {
                    "title": "My Show",
                    "author-name": "Author",
                    "description": "Desc",
                    "episodes": [{"file": "ep01.mp3"}],
                }
            ),
            encoding="utf-8",
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        proc = PodcastProcessor()
        ok = proc.process_podcast("myshow", cfg)
        assert ok is True
        assert not (tmp_path / "myshow.xml").exists()
        assert any("Validated" in record.message for record in caplog.records)


class TestMissingEpisodeFiles:
    def _write_config(self, tmp_path, episodes):
        cfg = tmp_path / "myshow-podcast.yaml"
        data = {"title": "My Show", "author-name": "Author", "description": "Desc"}
        if episodes is not None:
            data["episodes"] = episodes
        cfg.write_text(yaml.safe_dump(data), encoding="utf-8")
        return cfg

    def test_skips_missing_episode_file(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        cfg = self._write_config(tmp_path, [{"file": "ep01.mp3"}, {"file": "ep02.mp3"}])
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        ok = PodcastProcessor().process_podcast("myshow", cfg)
        assert ok is True
        xml = (tmp_path / "myshow.xml").read_text(encoding="utf-8")
        assert xml.count("<item>") == 1
        assert "ep01.mp3" in xml
        assert "ep02.mp3" not in xml
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
        assert "myshow" in warnings[0].message
        assert "ep02.mp3" in warnings[0].message
        assert any("Published myshow: 1 episodes" in r.message and "1 skipped" in r.message for r in caplog.records)

    def test_all_episode_files_missing(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        cfg = self._write_config(tmp_path, [{"file": "ep01.mp3"}, {"file": "ep02.mp3"}])
        (tmp_path / "myshow").mkdir()
        ok = PodcastProcessor().process_podcast("myshow", cfg)
        assert ok is False
        assert not (tmp_path / "myshow.xml").exists()
        assert any("No episodes found for myshow" in r.message for r in caplog.records)

    def test_auto_discovered_episodes_unaffected(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        cfg = self._write_config(tmp_path, None)
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        (pub / "ep02.mp3").write_bytes(b"\x00" * 64)
        ok = PodcastProcessor().process_podcast("myshow", cfg)
        assert ok is True
        xml = (tmp_path / "myshow.xml").read_text(encoding="utf-8")
        assert xml.count("<item>") == 2
        assert not any(r.levelname == "WARNING" for r in caplog.records)
        assert not any("skipped" in r.message for r in caplog.records)


class TestProcessAllPodcasts:
    def test_empty(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        proc = PodcastProcessor()
        failed = proc.process_all_podcasts()
        assert failed == 0
        assert any(record.levelname == "INFO" for record in caplog.records)

    def test_multiple(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        # first podcast
        cfg1 = tmp_path / "one-podcast.yaml"
        cfg1.write_text(
            yaml.safe_dump(
                {
                    "title": "One",
                    "author-name": "A",
                    "description": "D",
                    "episodes": [{"file": "ep.mp3"}],
                }
            ),
            encoding="utf-8",
        )
        pub1 = tmp_path / "one"
        pub1.mkdir()
        (pub1 / "ep.mp3").write_bytes(b"\x00" * 64)
        # second podcast
        cfg2 = tmp_path / "two-podcast.yaml"
        cfg2.write_text(
            yaml.safe_dump(
                {
                    "title": "Two",
                    "author-name": "B",
                    "description": "D",
                    "episodes": [{"file": "ep.mp3"}],
                }
            ),
            encoding="utf-8",
        )
        pub2 = tmp_path / "two"
        pub2.mkdir()
        (pub2 / "ep.mp3").write_bytes(b"\x00" * 64)
        proc = PodcastProcessor()
        failed = proc.process_all_podcasts()
        assert failed == 0
        assert (tmp_path / "one.xml").exists()
        assert (tmp_path / "two.xml").exists()

    def test_partial_failure(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        # good podcast
        cfg1 = tmp_path / "good-podcast.yaml"
        cfg1.write_text(
            yaml.safe_dump(
                {
                    "title": "Good",
                    "author-name": "A",
                    "description": "D",
                    "episodes": [{"file": "ep.mp3"}],
                }
            ),
            encoding="utf-8",
        )
        pub1 = tmp_path / "good"
        pub1.mkdir()
        (pub1 / "ep.mp3").write_bytes(b"\x00" * 64)
        # bad podcast (missing public dir)
        cfg2 = tmp_path / "bad-podcast.yaml"
        cfg2.write_text(
            yaml.safe_dump({"title": "Bad", "author-name": "B", "description": "D"}),
            encoding="utf-8",
        )
        proc = PodcastProcessor()
        failed = proc.process_all_podcasts()
        assert failed == 1
        assert any("1/2 successful" in record.message for record in caplog.records)


def _setup_show(tmp_path, monkeypatch):
    monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
    monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
    monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
    cfg = tmp_path / "myshow-podcast.yaml"
    cfg.write_text(
        yaml.safe_dump({"title": "T", "description": "D", "episodes": [{"file": "ep.mp3"}]}),
        encoding="utf-8",
    )
    pub = tmp_path / "myshow"
    pub.mkdir()
    (pub / "ep.mp3").write_bytes(b"\x00" * 64)
    return cfg


class TestAtomicWrite:
    def test_temp_file_is_hidden_and_synced_before_replace(self, tmp_path, monkeypatch, mocker):
        cfg = _setup_show(tmp_path, monkeypatch)
        events = []
        real_replace = os.replace
        real_fsync = os.fsync

        def fake_fsync(fd):
            events.append(("fsync", None))
            real_fsync(fd)

        def fake_replace(src, dst):
            if str(dst).endswith(".xml"):
                events.append(("replace", os.path.basename(src)))
            real_replace(src, dst)

        mocker.patch("podcastify.cli.os.fsync", side_effect=fake_fsync)
        mocker.patch("podcastify.cli.os.replace", side_effect=fake_replace)
        assert PodcastProcessor().process_podcast("myshow", cfg) is True
        assert [e[0] for e in events] == ["fsync", "replace"]
        temp_name = events[1][1]
        assert temp_name.startswith(".myshow.")
        assert temp_name.endswith(".xml.tmp")
        assert (tmp_path / "myshow.xml").exists()
        assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]

    def test_temp_file_removed_when_replace_fails(self, tmp_path, monkeypatch, mocker):
        cfg = _setup_show(tmp_path, monkeypatch)
        mocker.patch("podcastify.cli.os.replace", side_effect=OSError("disk gone"))
        assert PodcastProcessor().process_podcast("myshow", cfg) is False
        assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
        assert not (tmp_path / "myshow.xml").exists()


class TestUnchangedFeed:
    def _clock(self, mocker, *moments):
        class SteppingDatetime(datetime):
            ticks = iter(moments)

            @classmethod
            def now(cls, tz=None):
                return next(cls.ticks)

        mocker.patch("podcastify.rss.datetime", SteppingDatetime)

    def test_unchanged_content_keeps_the_existing_feed(self, tmp_path, monkeypatch, mocker, caplog):
        cfg = _setup_show(tmp_path, monkeypatch)
        self._clock(mocker, datetime(2030, 1, 1, tzinfo=timezone.utc), datetime(2030, 1, 2, tzinfo=timezone.utc))
        assert PodcastProcessor().process_podcast("myshow", cfg) is True
        feed = tmp_path / "myshow.xml"
        first = feed.read_text(encoding="utf-8")
        inode = feed.stat().st_ino
        assert PodcastProcessor().process_podcast("myshow", cfg) is True
        assert feed.read_text(encoding="utf-8") == first
        assert feed.stat().st_ino == inode
        assert "01 Jan 2030" in first
        assert any("Unchanged myshow" in r.message for r in caplog.records)
        assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]

    def test_changed_content_rewrites_the_feed(self, tmp_path, monkeypatch, mocker):
        cfg = _setup_show(tmp_path, monkeypatch)
        self._clock(mocker, datetime(2030, 1, 1, tzinfo=timezone.utc), datetime(2030, 1, 2, tzinfo=timezone.utc))
        assert PodcastProcessor().process_podcast("myshow", cfg) is True
        (tmp_path / "myshow" / "ep2.mp3").write_bytes(b"\x00" * 64)
        cfg.write_text(
            yaml.safe_dump({"title": "T", "description": "D", "episodes": [{"file": "ep.mp3"}, {"file": "ep2.mp3"}]}),
            encoding="utf-8",
        )
        assert PodcastProcessor().process_podcast("myshow", cfg) is True
        xml = (tmp_path / "myshow.xml").read_text(encoding="utf-8")
        assert "ep2.mp3" in xml
        assert "02 Jan 2030" in xml

    def test_undecodable_existing_feed_is_replaced(self, tmp_path, monkeypatch):
        cfg = _setup_show(tmp_path, monkeypatch)
        feed = tmp_path / "myshow.xml"
        feed.write_bytes(b"\xff\xfe broken")
        assert PodcastProcessor().process_podcast("myshow", cfg) is True
        assert "<rss" in feed.read_text(encoding="utf-8")


class TestStaleTempFiles:
    def _age(self, path, seconds):
        old = time.time() - seconds
        os.utime(path, (old, old))

    def test_old_temp_files_are_removed_at_start(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path / "none")
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        stale = tmp_path / ".myshow.abc123.xml.tmp"
        fresh = tmp_path / ".other.def456.xml.tmp"
        user_hidden = tmp_path / ".notes.xml"
        feed = tmp_path / "myshow.xml"
        for p in (stale, fresh, user_hidden, feed):
            p.write_text("x", encoding="utf-8")
        self._age(stale, 3600)
        self._age(user_hidden, 3600)
        self._age(feed, 3600)
        PodcastProcessor().process_all_podcasts()
        assert not stale.exists()
        assert fresh.exists()
        assert user_hidden.exists()
        assert feed.exists()

    def test_dry_run_keeps_old_temp_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path / "none")
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        stale = tmp_path / ".myshow.abc123.xml.tmp"
        stale.write_text("x", encoding="utf-8")
        self._age(stale, 3600)
        PodcastProcessor(dry_run=True).process_all_podcasts()
        assert stale.exists()

    def test_publishing_disabled_keeps_old_temp_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path / "none")
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", False)
        stale = tmp_path / ".myshow.abc123.xml.tmp"
        stale.write_text("x", encoding="utf-8")
        self._age(stale, 3600)
        PodcastProcessor().process_all_podcasts()
        assert stale.exists()

    def test_missing_public_root_is_fine(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path / "none")
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path / "missing")
        assert PodcastProcessor().process_all_podcasts() == 0

    def test_unremovable_temp_file_only_warns(self, tmp_path, monkeypatch, mocker, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path / "none")
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        stale = tmp_path / ".myshow.abc123.xml.tmp"
        stale.write_text("x", encoding="utf-8")
        self._age(stale, 3600)
        mocker.patch("pathlib.Path.unlink", side_effect=OSError("denied"))
        assert PodcastProcessor().process_all_podcasts() == 0
        assert any("denied" in r.message and r.levelname == "WARNING" for r in caplog.records)

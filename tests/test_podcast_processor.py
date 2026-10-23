#!/usr/bin/env python3
"""Tests for PodcastProcessor class."""

import yaml

from podcastify.cli import PodcastProcessor
from podcastify.config import Config


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
        assert any(record.levelname == "ERROR" for record in caplog.records)

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
        assert any("validation" in record.message.lower() for record in caplog.records)

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
        assert any(
            "Published myshow: 1 episodes" in r.message and "1 skipped" in r.message
            for r in caplog.records
        )

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

#!/usr/bin/env python3
"""Integration tests for the full application flow."""

import pytest

from podcastify.cli import main

CONFIG = b"title: My Show\nauthor-name: A\ndescription: D\n"


def _add_podcast(root, name="myshow"):
    (root / f"{name}-podcast.yaml").write_bytes(CONFIG)
    pub = root / name
    pub.mkdir()
    (pub / "ep01.mp3").write_bytes(b"\x00" * 64)


class TestMain:
    def test_run_on_start_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", True)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        _add_podcast(tmp_path)
        assert main([]) == 0
        assert (tmp_path / "myshow.xml").exists()

    def test_run_on_start_false_no_arg(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", False)
        assert main([]) == 0

    def test_generate_argument(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", False)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        _add_podcast(tmp_path)
        assert main(["generate"]) == 0
        assert (tmp_path / "myshow.xml").exists()

    def test_generate_dry_run_writes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", False)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        _add_podcast(tmp_path)
        assert main(["generate", "--dry-run"]) == 0
        assert not (tmp_path / "myshow.xml").exists()

    def test_unquoted_pub_dates_sort_and_render_consistently(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        (tmp_path / "myshow-podcast.yaml").write_text(
            "title: My Show\n"
            "description: D\n"
            "episodes:\n"
            "  - {file: a.mp3, title: Old, pub_date: 2025-01-01}\n"
            "  - {file: b.mp3, title: New, pub_date: 2025-03-01T08:00:00}\n"
            "  - {file: c.mp3, title: Mid, pub_date: '2025-02-01T08:00:00+02:00'}\n",
            encoding="utf-8",
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        for name in ("a", "b", "c"):
            (pub / f"{name}.mp3").write_bytes(b"\x00" * 64)
        assert main(["generate"]) == 0
        xml = (tmp_path / "myshow.xml").read_text(encoding="utf-8")
        assert xml.index("<title>New</title>") < xml.index("<title>Mid</title>") < xml.index("<title>Old</title>")
        assert "<pubDate>Sat, 01 Mar 2025 08:00:00 +0000</pubDate>" in xml
        assert "<pubDate>Sat, 01 Feb 2025 06:00:00 +0000</pubDate>" in xml
        assert "<pubDate>Wed, 01 Jan 2025 00:00:00 +0000</pubDate>" in xml

    def test_duplicate_episode_rejects_podcast(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        (tmp_path / "myshow-podcast.yaml").write_text(
            "title: T\ndescription: D\nepisodes:\n  - {file: a.mp3}\n  - {file: a.mp3}\n",
            encoding="utf-8",
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "a.mp3").write_bytes(b"\x00" * 64)
        assert main(["generate"]) == 1
        assert not (tmp_path / "myshow.xml").exists()
        assert any("duplicate episode file 'a.mp3'" in r.message for r in caplog.records)

    def test_no_configs_exits_zero(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", True)
        assert main([]) == 0
        assert main(["generate"]) == 0

    def test_partial_failure_exits_one(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", False)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        _add_podcast(tmp_path, "good")
        (tmp_path / "bad-podcast.yaml").write_bytes(CONFIG)
        assert main(["generate"]) == 1
        assert (tmp_path / "good.xml").exists()

    def test_all_failed_exits_one(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        (tmp_path / "bad-podcast.yaml").write_bytes(CONFIG)
        assert main(["generate"]) == 1

    @pytest.mark.parametrize(
        "argv",
        [["bogus"], ["--nope"], ["generate", "--nope"], ["--dry-run"]],
    )
    def test_usage_error_exits_two(self, argv, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 2
        assert "usage:" in capsys.readouterr().err

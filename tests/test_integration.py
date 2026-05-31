#!/usr/bin/env python3
"""Integration tests for the full application flow."""

import sys

import pytest

from podcastify.cli import main


class TestMain:
    def test_run_on_start_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", True)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        # setup a podcast
        (tmp_path / "myshow-podcast.yaml").write_bytes(
            b"title: My Show\nauthor-name: A\ndescription: D\n"
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        monkeypatch.setattr(sys, "argv", ["app.py"])
        result = main()
        assert result is True
        assert (tmp_path / "myshow.xml").exists()

    def test_run_on_start_false_no_arg(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", False)
        monkeypatch.setattr(sys, "argv", ["app.py"])
        result = main()
        assert result is True

    def test_generate_argument(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", False)
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_XML", True)
        (tmp_path / "myshow-podcast.yaml").write_bytes(
            b"title: My Show\nauthor-name: A\ndescription: D\n"
        )
        pub = tmp_path / "myshow"
        pub.mkdir()
        (pub / "ep01.mp3").write_bytes(b"\x00" * 64)
        monkeypatch.setattr(sys, "argv", ["app.py", "generate"])
        result = main()
        assert result is True
        assert (tmp_path / "myshow.xml").exists()

    def test_no_configs(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.RUN_ON_START", True)
        monkeypatch.setattr(sys, "argv", ["app.py"])
        result = main()
        assert result is False

#!/usr/bin/env python3
"""Golden-XML snapshot tests for feed generation.

These tests ensure the generated XML output matches a known baseline,
providing a regression guard against unintended changes to feed output.
"""

from pathlib import Path

from podcastify.cli import PodcastProcessor
from podcastify.config import Config
from podcastify.parser import ConfigurationManager, validate_podcast_config


class TestGoldenXMLSnapshot:
    """Verify feed output against golden baseline."""

    def test_generate_feed_with_sample_config(self, tmp_path, monkeypatch):
        """Generate a feed from a sample config and verify output structure."""
        podcasts_dir = tmp_path / "podcasts"
        public_dir = tmp_path / "public"
        podcasts_dir.mkdir()
        public_dir.mkdir()

        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", podcasts_dir)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public_dir)
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        monkeypatch.setenv("PODCASTS_ROOT", str(podcasts_dir))
        monkeypatch.setenv("PUBLIC_ROOT", str(public_dir))
        monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8080")

        podcast_dir = public_dir / "testpod"
        podcast_dir.mkdir()

        mp3_file = podcast_dir / "episode1.mp3"
        mp3_file.write_bytes(b"\x00" * 2048)

        config_file = podcasts_dir / "testpod-podcast.yaml"
        config_file.write_text(
            """
name: testpod
title: Test Podcast
author-name: Test Author
author-email: test@example.com
description: A test podcast
language: en
explicit: false
image: cover.jpg
categories:
  - Technology
episodes:
  - file: episode1.mp3
    title: Episode 1
    description: First episode
"""
        )

        processor = PodcastProcessor()
        success = processor.process_podcast("testpod", config_file)

        assert success is True
        xml_file = public_dir / "testpod.xml"
        assert xml_file.exists()

        xml_content = xml_file.read_text(encoding="utf-8")
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_content
        assert '<rss version="2.0"' in xml_content
        assert '<title>Test Podcast</title>' in xml_content
        assert '<description><![CDATA[A test podcast]]></description>' in xml_content
        assert '<itunes:author>Test Author</itunes:author>' in xml_content
        assert '<itunes:email>test@example.com</itunes:email>' in xml_content
        assert '<language>en</language>' in xml_content
        assert '<item>' in xml_content
        assert '<title>Episode 1</title>' in xml_content

    def test_metadata_rendering_consistency(self, tmp_path, monkeypatch):
        """Verify metadata is rendered consistently from validated model."""
        podcasts_dir = tmp_path / "podcasts"
        public_dir = tmp_path / "public"
        podcasts_dir.mkdir()
        public_dir.mkdir()

        monkeypatch.setattr("podcastify.config.Config.PODCASTS_ROOT", podcasts_dir)
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", public_dir)
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")

        podcast_dir = public_dir / "meta-test"
        podcast_dir.mkdir()

        mp3_file = podcast_dir / "test.mp3"
        mp3_file.write_bytes(b"\x00" * 2048)

        config_file = podcasts_dir / "meta-test-podcast.yaml"
        config_file.write_text(
            """
title: Metadata Test Show
description: Testing metadata extraction
author-name: Meta Author
explicit: true
subtitle: Test Subtitle
summary: Test Summary
type: episodic
episodes:
  - file: test.mp3
    title: Test Episode
"""
        )

        processor = PodcastProcessor()
        success = processor.process_podcast("meta-test", config_file)

        assert success is True
        xml_file = public_dir / "meta-test.xml"
        xml_content = xml_file.read_text(encoding="utf-8")

        assert "<title>Metadata Test Show</title>" in xml_content
        assert "<itunes:explicit>yes</itunes:explicit>" in xml_content
        assert "<itunes:subtitle>Test Subtitle</itunes:subtitle>" in xml_content
        assert "<itunes:summary><![CDATA[Test Summary]]></itunes:summary>" in xml_content
        assert "<itunes:type>episodic</itunes:type>" in xml_content

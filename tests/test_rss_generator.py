#!/usr/bin/env python3
"""Tests for RSSGenerator class."""

from datetime import datetime, timezone

import pytest

from podcastify.rss import RSSGenerator


class TestXmlEscape:
    def test_string(self):
        assert RSSGenerator.xml_escape("Hello & World") == "Hello &amp; World"

    def test_quotes(self):
        assert RSSGenerator.xml_escape('He said "hi"') == "He said &quot;hi&quot;"

    def test_none(self):
        assert RSSGenerator.xml_escape(None) == ""

    def test_int(self):
        assert RSSGenerator.xml_escape(42) == "42"


class TestBuildItunesCategories:
    def test_string(self):
        result = RSSGenerator.build_itunes_categories("Technology")
        assert 'text="Technology"' in result

    def test_list_of_strings(self):
        result = RSSGenerator.build_itunes_categories(["Technology", "Education"])
        assert 'text="Technology"' in result
        assert 'text="Education"' in result

    def test_nested_list(self):
        result = RSSGenerator.build_itunes_categories([["Society & Culture", "Personal Journals"]])
        assert 'text="Society &amp; Culture"' in result
        assert 'text="Personal Journals"' in result

    def test_dict_style(self):
        result = RSSGenerator.build_itunes_categories([{"name": "Technology", "sub": "Software How-To"}])
        assert 'text="Technology"' in result
        assert 'text="Software How-To"' in result

    def test_empty(self):
        assert RSSGenerator.build_itunes_categories("") == ""
        assert RSSGenerator.build_itunes_categories([]) == ""
        assert RSSGenerator.build_itunes_categories(None) == ""

    def test_dict_single(self):
        result = RSSGenerator.build_itunes_categories({"name": "Arts", "sub": "Books"})
        assert 'text="Arts"' in result
        assert 'text="Books"' in result


class TestGenerateFeedXml:
    def test_basic_structure(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        gen = RSSGenerator()
        xml = gen.generate_feed_xml(
            "myshow",
            {"title": "My Show", "description": "Test", "language": "en", "author-name": "Author"},
            [{"file": "ep01.mp3", "__resolved_path": pub_dir / "ep01.mp3"}],
        )
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert '<rss version="2.0"' in xml
        assert "<channel>" in xml
        assert "<item>" in xml
        assert "</rss>" in xml

    def test_channel_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_dir := tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        gen = RSSGenerator()
        channel = gen._build_channel_metadata(
            "myshow",
            {
                "title": "Title",
                "description": "Desc",
                "language": "fr",
                "author-name": "Author",
                "author-email": "a@b.com",
                "explicit": True,
                "subtitle": "Sub",
                "summary": "Sum",
                "categories": ["Arts"],
                "type": "serial",
                "block": True,
                "complete": True,
                "new_feed_url": "https://new.example.com/feed.xml",
            },
            "Mon, 01 Jan 2024 00:00:00 +0000",
        )
        assert "<title>Title</title>" in channel
        assert "<description><![CDATA[Desc]]></description>" in channel
        assert "<language>fr</language>" in channel
        assert "<itunes:explicit>yes</itunes:explicit>" in channel
        assert "<itunes:author>Author</itunes:author>" in channel
        assert "<itunes:name>Author</itunes:name>" in channel
        assert "<itunes:email>a@b.com</itunes:email>" in channel
        assert "<itunes:subtitle>Sub</itunes:subtitle>" in channel
        assert "<itunes:summary><![CDATA[Sum]]></itunes:summary>" in channel
        assert 'text="Arts"' in channel
        assert "<itunes:type>serial</itunes:type>" in channel
        assert "<itunes:block>yes</itunes:block>" in channel
        assert "<itunes:complete>yes</itunes:complete>" in channel
        assert "<itunes:new-feed-url>https://new.example.com/feed.xml</itunes:new-feed-url>" in channel

    def test_channel_no_optional_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        gen = RSSGenerator()
        channel = gen._build_channel_metadata(
            "myshow",
            {"title": "Title", "description": "", "author-name": "", "explicit": False},
            "Mon, 01 Jan 2024 00:00:00 +0000",
        )
        assert "<title>Title</title>" in channel
        assert "<itunes:explicit>no</itunes:explicit>" in channel
        assert "<itunes:subtitle>" not in channel
        assert "<itunes:owner>" not in channel

    def test_episode_item(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        gen = RSSGenerator()
        item = gen._build_episode_item(
            "myshow",
            {
                "file": "ep01.mp3",
                "title": "Episode 1",
                "description": "Desc",
                "pub_date": "2024-01-01T00:00:00Z",
                "explicit": True,
                "season": 1,
                "episode": 2,
                "episode_type": "full",
                "guid": "custom-guid",
                "__resolved_path": pub_dir / "ep01.mp3",
            },
            {"author-name": "Author", "explicit": False},
        )
        assert "<title>Episode 1</title>" in item
        assert "<description><![CDATA[Desc]]></description>" in item
        assert "<guid isPermaLink=\"false\">custom-guid</guid>" in item
        assert 'url="http://localhost:8080/myshow/ep01.mp3"' in item
        assert "<itunes:explicit>yes</itunes:explicit>" in item
        assert "<itunes:author>Author</itunes:author>" in item
        assert "<itunes:season>1</itunes:season>" in item
        assert "<itunes:episode>2</itunes:episode>" in item
        assert "<itunes:episodeType>full</itunes:episodeType>" in item

    def test_episode_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        gen = RSSGenerator()
        item = gen._build_episode_item(
            "myshow",
            {"file": "ep01.mp3", "__resolved_path": pub_dir / "ep01.mp3"},
            {"author-name": "Author", "explicit": False},
        )
        assert "<title>ep01</title>" in item  # stem of filename
        assert "<guid isPermaLink=\"false\">" in item
        assert "<itunes:explicit>no</itunes:explicit>" in item
        # No season/episode/type if not present
        assert "<itunes:season>" not in item
        assert "<itunes:episode>" not in item
        assert "<itunes:episodeType>" not in item

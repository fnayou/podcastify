#!/usr/bin/env python3
"""Tests for RSSGenerator class."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import pytest

from podcastify.rss import RSSGenerator

PUBLISHED = datetime(2024, 1, 1, tzinfo=timezone.utc)


class TestXmlEscape:
    def test_string(self):
        assert RSSGenerator.xml_escape("Hello & World") == "Hello &amp; World"

    def test_quotes(self):
        assert RSSGenerator.xml_escape('He said "hi"') == "He said &quot;hi&quot;"

    def test_none(self):
        assert RSSGenerator.xml_escape(None) == ""

    def test_int(self):
        assert RSSGenerator.xml_escape(42) == "42"

    def test_removes_illegal_xml_chars(self):
        assert RSSGenerator.xml_escape("a\x00b\x08c\x0bd\x0ce\x1ff￾g￿h\ti\nj") == "abcdefgh\ti\nj"


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
            [{"file": "ep01.mp3", "__resolved_path": pub_dir / "ep01.mp3", "__published": PUBLISHED}],
        )
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert '<rss version="2.0"' in xml
        assert "<channel>" in xml
        assert "<item>" in xml
        assert "</rss>" in xml

    def test_channel_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
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
                "__published": PUBLISHED,
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
        assert "<pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>" in item

    def test_episode_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        gen = RSSGenerator()
        item = gen._build_episode_item(
            "myshow",
            {"file": "ep01.mp3", "__resolved_path": pub_dir / "ep01.mp3", "__published": PUBLISHED},
            {"author-name": "Author", "explicit": False},
        )
        assert "<title>ep01</title>" in item  # stem of filename
        assert "<guid isPermaLink=\"false\">" in item
        assert "<itunes:explicit>no</itunes:explicit>" in item
        # No season/episode/type if not present
        assert "<itunes:season>" not in item
        assert "<itunes:episode>" not in item
        assert "<itunes:episodeType>" not in item


class TestEnclosureType:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("ep.mp3", "audio/mpeg"),
            ("ep.MP3", "audio/mpeg"),
            ("ep.m4a", "audio/x-m4a"),
            ("ep.mp4", "video/mp4"),
            ("ep.ogg", "audio/ogg"),
            ("ep.opus", "audio/opus"),
        ],
    )
    def test_enclosure_type_follows_extension(self, tmp_path, monkeypatch, name, expected):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / name).write_bytes(b"\x00" * 64)
        item = RSSGenerator()._build_episode_item(
            "myshow",
            {"file": name, "__resolved_path": pub_dir / name, "__published": PUBLISHED},
            {"author-name": "Author"},
        )
        assert f'type="{expected}"/>' in item


class TestMediaUrls:
    def test_enclosure_url_encoded_and_escaped_once(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com/feeds/")
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "Q&A #1?.mp3").write_bytes(b"\x00" * 64)
        item = RSSGenerator()._build_episode_item(
            "myshow",
            {
                "file": "Q&A #1?.mp3",
                "title": "T",
                "guid": "g",
                "__resolved_path": pub_dir / "Q&A #1?.mp3",
                "__published": PUBLISHED,
            },
            {"author-name": "Author"},
        )
        assert 'url="https://example.com/feeds/myshow/Q%26A%20%231%3F.mp3"' in item
        assert "&amp;" not in item

    def test_image_href_encoded(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "Café & co.jpg").write_bytes(b"\x00" * 64)
        channel = RSSGenerator()._build_channel_metadata(
            "myshow",
            {"title": "T", "image": "Café & co.jpg"},
            "Mon, 01 Jan 2024 00:00:00 +0000",
        )
        assert '<itunes:image href="http://localhost:8080/myshow/Caf%C3%A9%20%26%20co.jpg"/>' in channel


class TestFeedWellFormed:
    HOSTILE = 'Tom & "Jerry" <b>bold</b> it\'s ]]> café 日本語 🎙️\x01\x0b￾ end'
    CLEAN = 'Tom & "Jerry" <b>bold</b> it\'s ]]> café 日本語 🎙️ end'
    ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

    def test_cdata_end_sequence_is_split(self):
        channel = RSSGenerator()._build_channel_metadata(
            "myshow",
            {"title": "T", "description": "a]]>b"},
            "Mon, 01 Jan 2024 00:00:00 +0000",
        )
        assert "<description><![CDATA[a]]]]><![CDATA[>b]]></description>" in channel

    def test_hostile_text_produces_parseable_feed(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        pub_dir = tmp_path / "myshow"
        pub_dir.mkdir()
        (pub_dir / "ep01.mp3").write_bytes(b"\x00" * 64)
        xml = RSSGenerator().generate_feed_xml(
            "myshow",
            {
                "title": self.HOSTILE,
                "description": self.HOSTILE,
                "summary": self.HOSTILE,
                "subtitle": self.HOSTILE,
                "author-name": self.HOSTILE,
                "author-email": self.HOSTILE,
                "categories": [[self.HOSTILE, self.HOSTILE]],
            },
            [
                {
                    "file": "ep01.mp3",
                    "title": self.HOSTILE,
                    "description": self.HOSTILE,
                    "summary": self.HOSTILE,
                    "subtitle": self.HOSTILE,
                    "guid": self.HOSTILE,
                    "duration_hms": self.HOSTILE,
                    "__resolved_path": pub_dir / "ep01.mp3",
                    "__published": PUBLISHED,
                }
            ],
        )
        channel = ET.fromstring(xml.encode("utf-8")).find("channel")
        it = self.ITUNES
        for tag in ("title", "description", f"{it}summary", f"{it}subtitle", f"{it}author",
                    f"{it}owner/{it}name", f"{it}owner/{it}email"):
            assert channel.find(tag).text == self.CLEAN
        category = channel.find(f"{it}category")
        assert category.get("text") == self.CLEAN
        assert category.find(f"{it}category").get("text") == self.CLEAN
        item = channel.find("item")
        for tag in ("title", "description", "guid", f"{it}summary", f"{it}subtitle", f"{it}duration"):
            assert item.find(tag).text == self.CLEAN

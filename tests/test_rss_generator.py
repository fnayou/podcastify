#!/usr/bin/env python3
"""Tests for RSSGenerator class."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import pytest

from podcastify.parser import Episode, EpisodeModel, PodcastChannelModel
from podcastify.rss import RSSGenerator

PUBLISHED = datetime(2024, 1, 1, tzinfo=timezone.utc)
IT = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
ATOM = "{http://www.w3.org/2005/Atom}"

pytestmark = pytest.mark.usefixtures("fixed_duration")


def _channel(**fields):
    return PodcastChannelModel.model_validate({"title": "T", "description": "D", **fields})


def _episode(path, **fields):
    return Episode(EpisodeModel.model_validate({"file": path.name, **fields}), path, PUBLISHED)


def _xml(channel, episodes=(), podcast="myshow"):
    return RSSGenerator().generate_feed_xml(podcast, channel, list(episodes))


def _feed(channel, episodes=(), podcast="myshow"):
    return ET.fromstring(_xml(channel, episodes, podcast).encode("utf-8")).find("channel")


@pytest.fixture
def pub_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
    monkeypatch.setattr("podcastify.config.Config.BASE_URL", "http://localhost:8080")
    directory = tmp_path / "myshow"
    directory.mkdir()
    return directory


@pytest.fixture
def mp3(pub_dir):
    path = pub_dir / "ep01.mp3"
    path.write_bytes(b"\x00" * 64)
    return path


class TestStripIllegalXmlChars:
    def test_removes_illegal_xml_chars(self):
        assert RSSGenerator.strip_illegal_xml_chars("a\x00b\x08c\x0bd\x0ce\x1ff￾g￿h\ti\nj") == "abcdefgh\ti\nj"


class TestItunesCategories:
    def _categories(self, categories):
        channel = _feed(_channel(categories=categories))
        return [
            (c.get("text"), [s.get("text") for s in c.findall(f"{IT}category")])
            for c in channel.findall(f"{IT}category")
        ]

    def test_string(self, pub_dir):
        assert self._categories("Technology") == [("Technology", [])]

    def test_list_of_strings(self, pub_dir):
        assert self._categories(["Technology", "Education"]) == [("Technology", []), ("Education", [])]

    def test_nested_list(self, pub_dir):
        assert self._categories([["Society & Culture", "Personal Journals"]]) == [
            ("Society & Culture", ["Personal Journals"])
        ]

    def test_dict_style(self, pub_dir):
        assert self._categories([{"name": "Technology", "sub": "Software How-To"}]) == [
            ("Technology", ["Software How-To"])
        ]

    def test_dict_single(self, pub_dir):
        assert self._categories({"name": "Arts", "sub": "Books"}) == [("Arts", ["Books"])]

    @pytest.mark.parametrize("categories", ["", " ", [], None, [["Only parent"]], [{"sub": "x"}], [5]])
    def test_empty_or_unusable(self, pub_dir, categories):
        assert self._categories(categories) == []

    def test_non_string_sub_is_dropped(self, pub_dir):
        assert self._categories([["Arts", 5], {"name": "Music", "sub": " "}]) == [("Arts", []), ("Music", [])]


class TestGenerateFeedXml:
    def test_basic_structure(self, mp3):
        xml = _xml(_channel(**{"author-name": "Author"}), [_episode(mp3)])
        assert xml.startswith("<?xml version='1.0' encoding='utf-8'?>\n<rss ")
        assert 'xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"' in xml
        assert 'xmlns:content="http://purl.org/rss/1.0/modules/content/"' in xml
        assert 'xmlns:atom="http://www.w3.org/2005/Atom"' in xml
        root = ET.fromstring(xml.encode("utf-8"))
        assert root.tag == "rss"
        assert root.get("version") == "2.0"
        assert len(root.findall("./channel/item")) == 1

    def test_channel_metadata(self, pub_dir):
        channel = _feed(
            _channel(
                title="Title",
                description="Desc",
                language="fr",
                explicit=True,
                subtitle="Sub",
                summary="Sum",
                categories=["Arts"],
                type="serial",
                block=True,
                complete=True,
                new_feed_url="https://new.example.com/feed.xml",
                link="https://example.com/show",
                **{"author-name": "Author", "author-email": "a@b.com"},
            )
        )
        assert channel.findtext("title") == "Title"
        assert channel.findtext("link") == "https://example.com/show"
        assert channel.findtext("description") == "Desc"
        assert channel.findtext("language") == "fr"
        assert channel.findtext("generator") == "podcastify"
        assert channel.findtext(f"{IT}explicit") == "true"
        assert channel.findtext(f"{IT}author") == "Author"
        assert channel.findtext(f"{IT}owner/{IT}name") == "Author"
        assert channel.findtext(f"{IT}owner/{IT}email") == "a@b.com"
        assert channel.findtext(f"{IT}subtitle") == "Sub"
        assert channel.findtext(f"{IT}summary") == "Sum"
        assert channel.find(f"{IT}category").get("text") == "Arts"
        assert channel.findtext(f"{IT}type") == "serial"
        assert channel.findtext(f"{IT}block") == "yes"
        assert channel.findtext(f"{IT}complete") == "yes"
        assert channel.findtext(f"{IT}new-feed-url") == "https://new.example.com/feed.xml"

    def test_channel_defaults(self, pub_dir):
        channel = _feed(_channel(title="", description=" ", language=None, explicit=None))
        assert channel.findtext("title") == "myshow"
        assert channel.findtext("link") == "http://localhost:8080"
        assert channel.find("description") is None
        assert channel.findtext("language") == "en"
        assert channel.findtext(f"{IT}explicit") == "false"
        tags = (
            "author",
            "summary",
            "subtitle",
            "owner",
            "image",
            "category",
            "type",
            "block",
            "complete",
            "new-feed-url",
        )
        for tag in tags:
            assert channel.find(f"{IT}{tag}") is None

    def test_self_link(self, pub_dir):
        link = _feed(_channel()).find(f"{ATOM}link")
        assert link.attrib == {"href": "http://localhost:8080/myshow.xml", "rel": "self", "type": "application/rss+xml"}

    def test_self_link_quotes_name(self, pub_dir):
        link = _feed(_channel(), podcast="my show").find(f"{ATOM}link")
        assert link.get("href") == "http://localhost:8080/my%20show.xml"

    def test_no_empty_elements(self, mp3):
        root = ET.fromstring(_xml(_channel(description=" "), [_episode(mp3)]).encode("utf-8"))
        empty = [e.tag for e in root.iter() if not e.attrib and not len(e) and not (e.text or "").strip()]
        assert empty == []

    def test_owner_with_email_only(self, pub_dir):
        owner = _feed(_channel(**{"author-email": "a@b.com"})).find(f"{IT}owner")
        assert owner.find(f"{IT}name") is None
        assert owner.findtext(f"{IT}email") == "a@b.com"

    def test_episode_item(self, mp3):
        item = _feed(
            _channel(**{"author-name": "Author"}),
            [
                _episode(
                    mp3,
                    title="Episode 1",
                    description="Desc",
                    explicit=True,
                    season=1,
                    episode=2,
                    episode_type="full",
                    guid="custom-guid",
                    subtitle="Sub",
                )
            ],
        ).find("item")
        assert item.findtext("title") == "Episode 1"
        assert item.findtext("description") == "Desc"
        assert item.findtext("guid") == "custom-guid"
        assert item.find("guid").get("isPermaLink") == "false"
        enclosure = item.find("enclosure")
        assert enclosure.get("url") == "http://localhost:8080/myshow/ep01.mp3"
        assert enclosure.get("length") == "64"
        assert enclosure.get("type") == "audio/mpeg"
        assert item.findtext(f"{IT}explicit") == "true"
        assert item.findtext(f"{IT}author") == "Author"
        assert item.findtext(f"{IT}subtitle") == "Sub"
        assert item.findtext(f"{IT}summary") == "Desc"
        assert item.findtext(f"{IT}season") == "1"
        assert item.findtext(f"{IT}episode") == "2"
        assert item.findtext(f"{IT}episodeType") == "full"
        assert item.findtext("pubDate") == "Mon, 01 Jan 2024 00:00:00 +0000"

    def test_episode_defaults(self, mp3):
        item = _feed(_channel(explicit=True, **{"author-name": "Author"}), [_episode(mp3)]).find("item")
        assert item.findtext("title") == "ep01"
        assert len(item.findtext("guid")) == 40
        assert item.find("description") is None
        assert item.findtext(f"{IT}explicit") == "true"
        assert item.findtext(f"{IT}author") == "Author"
        assert item.findtext(f"{IT}duration") == "0:42"
        for tag in ("summary", "subtitle", "image", "season", "episode", "episodeType"):
            assert item.find(f"{IT}{tag}") is None

    def test_episode_overrides_channel(self, mp3):
        item = _feed(
            _channel(explicit=True, **{"author-name": "Author"}),
            [_episode(mp3, explicit=False, duration_hms="1:00", **{"author-name": "Guest"})],
        ).find("item")
        assert item.findtext(f"{IT}explicit") == "false"
        assert item.findtext(f"{IT}author") == "Guest"
        assert item.findtext(f"{IT}duration") == "1:00"

    def test_unknown_episode_type_is_dropped(self, mp3):
        item = _feed(_channel(), [_episode(mp3, episode_type="special")]).find("item")
        assert item.find(f"{IT}episodeType") is None

    def test_missing_file_has_zero_length_and_no_duration(self, pub_dir):
        item = _feed(_channel(), [_episode(pub_dir / "gone.mp3")]).find("item")
        assert item.find("enclosure").get("length") == "0"
        assert item.find(f"{IT}duration") is None

    def test_episode_image(self, mp3):
        (mp3.parent / "art.png").write_bytes(b"\x00")
        item = _feed(_channel(), [_episode(mp3, image="art.png")]).find("item")
        assert item.find(f"{IT}image").get("href") == "http://localhost:8080/myshow/art.png"


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
    def test_enclosure_type_follows_extension(self, pub_dir, name, expected):
        path = pub_dir / name
        path.write_bytes(b"\x00" * 64)
        item = _feed(_channel(), [_episode(path)]).find("item")
        assert item.find("enclosure").get("type") == expected


class TestMediaUrls:
    def test_enclosure_url_encoded_and_escaped_once(self, pub_dir, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.BASE_URL", "https://example.com/feeds")
        path = pub_dir / "Q&A #1?.mp3"
        path.write_bytes(b"\x00" * 64)
        xml = _xml(_channel(), [_episode(path, title="T", guid="g")])
        assert 'url="https://example.com/feeds/myshow/Q%26A%20%231%3F.mp3"' in xml
        assert "&amp;" not in xml

    def test_image_href_encoded(self, pub_dir):
        (pub_dir / "Café & co.jpg").write_bytes(b"\x00" * 64)
        channel = _feed(_channel(image="Café & co.jpg"))
        assert channel.find(f"{IT}image").get("href") == "http://localhost:8080/myshow/Caf%C3%A9%20%26%20co.jpg"


class TestFeedWellFormed:
    HOSTILE = 'Tom & "Jerry" <b>bold</b> it\'s ]]> café 日本語 🎙️\x01\x0b￾ end'
    CLEAN = 'Tom & "Jerry" <b>bold</b> it\'s ]]> café 日本語 🎙️ end'

    def test_cdata_end_sequence_round_trips(self, pub_dir):
        xml = _xml(_channel(description="a]]>b"))
        assert "<description>a]]&gt;b</description>" in xml
        assert ET.fromstring(xml.encode("utf-8")).findtext("./channel/description") == "a]]>b"

    def test_hostile_text_produces_parseable_feed(self, mp3):
        hostile = self.HOSTILE
        channel = _feed(
            _channel(
                title=hostile,
                description=hostile,
                summary=hostile,
                subtitle=hostile,
                categories=[[hostile, hostile]],
                **{"author-name": hostile, "author-email": hostile},
            ),
            [
                _episode(
                    mp3,
                    title=hostile,
                    description=hostile,
                    summary=hostile,
                    subtitle=hostile,
                    guid=hostile,
                    duration_hms=hostile,
                )
            ],
        )
        for tag in (
            "title",
            "description",
            f"{IT}summary",
            f"{IT}subtitle",
            f"{IT}author",
            f"{IT}owner/{IT}name",
            f"{IT}owner/{IT}email",
        ):
            assert channel.find(tag).text == self.CLEAN
        category = channel.find(f"{IT}category")
        assert category.get("text") == self.CLEAN
        assert category.find(f"{IT}category").get("text") == self.CLEAN
        item = channel.find("item")
        for tag in ("title", "description", "guid", f"{IT}summary", f"{IT}subtitle", f"{IT}duration"):
            assert item.find(tag).text == self.CLEAN

from pathlib import Path
from xml.etree import ElementTree

import pytest

from podcastify.cli import PodcastProcessor

GOLDEN_DIR = Path(__file__).parent / "golden"

BASIC_CONFIG = """
name: basic
title: Basic Show
author-name: Test Author
author-email: test@example.com
description: A basic show
language: en
explicit: false
subtitle: Short line
type: episodic
categories:
  - Technology
episodes:
  - file: episode1.mp3
    title: Episode 1
    description: First episode
    pub_date: 2029-05-06T07:08:09+00:00
    duration_hms: "00:10:00"
    guid: basic-guid-1
    season: 1
    episode: 1
    episode_type: full
  - file: episode2.mp3
    title: Episode 2
    pub_date: 2029-06-07
"""

HOSTILE_CONFIG = """
name: hostile
title: "Fish & Chips <live> \\"quoted\\" \\x01"
author-name: "Zoë & Søren"
author-email: "zoe+test@example.com"
description: "Close CDATA with ]]> early & often, é 日本語 🎙"
summary: "Sum ]]> mary & <b>bold</b>"
subtitle: "Sub & title"
categories:
  - [Arts, Food & Drink]
  - name: Society & Culture
    sub: Philosophy
  - Business
episodes:
  - file: "Épisode 1 & café #1.mp3"
    title: "Ep <1> & \\"café\\""
    description: "Desc ]]> with & ampersand and 日本語"
    pub_date: 2029-05-06T07:08:09+02:00
    duration_hms: "00:01:05"
    author-name: "Ep & Author"
  - file: "plain episode.mp3"
    title: Plain
    pub_date: 2029-06-07T00:00:00
"""


def _media(public: Path, podcast: str, names: list) -> None:
    pod_dir = public / podcast
    pod_dir.mkdir()
    for index, name in enumerate(names, start=1):
        (pod_dir / name).write_bytes(b"\x00" * (1000 * index))


def _generate(golden_roots, podcast: str, config: str, media: list) -> str:
    podcasts, public = golden_roots
    _media(public, podcast, media)
    config_file = podcasts / f"{podcast}-podcast.yaml"
    config_file.write_text(config, encoding="utf-8")
    assert PodcastProcessor().process_podcast(podcast, config_file) is True
    return (public / f"{podcast}.xml").read_text(encoding="utf-8")


CASES = [
    pytest.param("basic", BASIC_CONFIG, ["episode1.mp3", "episode2.mp3"], id="basic"),
    pytest.param(
        "hostile",
        HOSTILE_CONFIG,
        ["Épisode 1 & café #1.mp3", "plain episode.mp3"],
        id="hostile",
    ),
]


@pytest.mark.usefixtures("frozen_clock")
class TestGoldenXML:
    @pytest.mark.parametrize("podcast, config, media", CASES)
    def test_output_matches_snapshot(self, golden_roots, podcast, config, media):
        xml = _generate(golden_roots, podcast, config, media)
        expected = (GOLDEN_DIR / f"{podcast}.xml").read_text(encoding="utf-8")
        assert xml == expected

    @pytest.mark.parametrize("podcast, config, media", CASES)
    def test_output_is_well_formed(self, golden_roots, podcast, config, media):
        xml = _generate(golden_roots, podcast, config, media)
        root = ElementTree.fromstring(xml.encode("utf-8"))
        assert root.tag == "rss"
        assert len(root.findall("./channel/item")) == 2

    def test_hostile_text_round_trips(self, golden_roots):
        xml = _generate(golden_roots, "hostile", HOSTILE_CONFIG, CASES[1].values[2])
        channel = ElementTree.fromstring(xml.encode("utf-8")).find("channel")
        assert channel.findtext("title") == 'Fish & Chips <live> "quoted" '
        assert channel.findtext("description") == "Close CDATA with ]]> early & often, é 日本語 🎙"
        item = channel.findall("item")[1]
        assert item.findtext("description") == "Desc ]]> with & ampersand and 日本語"
        assert item.find("enclosure").get("url") == (
            "http://localhost:8080/hostile/%C3%89pisode%201%20%26%20caf%C3%A9%20%231.mp3"
        )

    def test_hostile_nested_categories(self, golden_roots):
        xml = _generate(golden_roots, "hostile", HOSTILE_CONFIG, CASES[1].values[2])
        root = ElementTree.fromstring(xml.encode("utf-8"))
        ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
        tops = root.findall("./channel/itunes:category", ns)
        assert [c.get("text") for c in tops] == ["Arts", "Society & Culture", "Business"]
        assert [c.get("text") for c in tops[0].findall("itunes:category", ns)] == ["Food & Drink"]
        assert [c.get("text") for c in tops[1].findall("itunes:category", ns)] == ["Philosophy"]

    def test_clock_and_durations_are_deterministic(self, golden_roots):
        xml = _generate(golden_roots, "basic", BASIC_CONFIG, CASES[0].values[2])
        root = ElementTree.fromstring(xml.encode("utf-8"))
        ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
        assert root.findtext("./channel/lastBuildDate") == "Wed, 02 Jan 2030 03:04:05 +0000"
        durations = [d.text for d in root.findall("./channel/item/itunes:duration", ns)]
        assert durations == ["0:42", "00:10:00"]

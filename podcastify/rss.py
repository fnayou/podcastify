import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

from podcastify.config import Config
from podcastify.media import MediaProcessor
from podcastify.parser import (
    Episode,
    EpisodeManager,
    PodcastChannelModel,
    rfc2822_date,
)

logger = logging.getLogger(__name__)

_ILLEGAL_XML_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
IT = f"{{{ITUNES_NS}}}"
ATOM_NS = "http://www.w3.org/2005/Atom"
ATOM = f"{{{ATOM_NS}}}"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
EPISODE_TYPES = ("full", "trailer", "bonus")

ET.register_namespace("itunes", ITUNES_NS)
ET.register_namespace("atom", ATOM_NS)


class RSSGenerator:
    @staticmethod
    def strip_illegal_xml_chars(value: str) -> str:
        return _ILLEGAL_XML_CHARS.sub("", value)

    @classmethod
    def _add(
        cls,
        parent: ET.Element,
        tag: str,
        text: Optional[str] = None,
        attrib: Optional[Dict[str, str]] = None,
    ) -> ET.Element:
        element = ET.SubElement(
            parent, tag, {key: cls.strip_illegal_xml_chars(value) for key, value in (attrib or {}).items()}
        )
        if text is not None:
            element.text = cls.strip_illegal_xml_chars(text)
        return element

    @classmethod
    def _add_optional(cls, parent: ET.Element, tag: str, text: Optional[str]) -> None:
        cleaned = cls.strip_illegal_xml_chars(text) if text else ""
        if cleaned.strip():
            cls._add(parent, tag, cleaned)

    @staticmethod
    def _explicit(value: bool) -> str:
        return "true" if value else "false"

    @classmethod
    def _add_categories(cls, parent: ET.Element, categories: Union[str, List[Any], Dict[str, Any], None]) -> None:
        def add_category(name: Any, sub: Any = None) -> None:
            if not isinstance(name, str) or not name.strip():
                return
            category = cls._add(parent, f"{IT}category", attrib={"text": name})
            if isinstance(sub, str) and sub.strip():
                cls._add(category, f"{IT}category", attrib={"text": sub})

        for item in categories if isinstance(categories, list) else [categories]:
            if isinstance(item, str):
                add_category(item)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                add_category(item[0], item[1])
            elif isinstance(item, dict):
                add_category(item.get("name"), item.get("sub"))

    def generate_feed_xml(self, podcast_name: str, channel: PodcastChannelModel, episodes: List[Episode]) -> str:
        logger.debug(f"Render channel: {podcast_name}")
        rss = ET.Element("rss", {"version": "2.0", "xmlns:content": CONTENT_NS})
        channel_element = self._build_channel(rss, podcast_name, channel)
        for episode in episodes:
            logger.debug(f"Build episode item: {episode.model.file}")
            self._build_item(channel_element, podcast_name, episode, channel)
        ET.indent(rss, space="  ")
        return ET.tostring(rss, encoding="unicode", xml_declaration=True)

    def _build_channel(self, rss: ET.Element, podcast_name: str, channel: PodcastChannelModel) -> ET.Element:
        add = self._add
        element = add(rss, "channel")
        add(element, "title", channel.title or podcast_name)
        add(element, "link", channel.link or Config.BASE_URL)
        add(
            element,
            f"{ATOM}link",
            attrib={
                "href": f"{Config.BASE_URL}/{quote(podcast_name)}.xml",
                "rel": "self",
                "type": "application/rss+xml",
            },
        )
        self._add_optional(element, "description", channel.description)
        add(element, "language", channel.language)
        add(element, "generator", "podcastify")
        add(element, "lastBuildDate", rfc2822_date(datetime.now(timezone.utc)))
        add(element, f"{IT}explicit", self._explicit(channel.explicit))
        self._add_optional(element, f"{IT}author", channel.author_name)

        self._add_optional(element, f"{IT}subtitle", channel.subtitle)
        self._add_optional(element, f"{IT}summary", channel.summary or channel.description)

        image = EpisodeManager.resolve_image_url(podcast_name, channel.image)
        if image:
            add(element, f"{IT}image", attrib={"href": image})

        if channel.author_name or channel.author_email:
            owner = add(element, f"{IT}owner")
            if channel.author_name:
                add(owner, f"{IT}name", channel.author_name)
            if channel.author_email:
                add(owner, f"{IT}email", channel.author_email)

        self._add_categories(element, channel.categories)

        if channel.type:
            add(element, f"{IT}type", channel.type)
        if channel.block:
            add(element, f"{IT}block", "yes")
        if channel.complete:
            add(element, f"{IT}complete", "yes")
        if channel.new_feed_url:
            add(element, f"{IT}new-feed-url", channel.new_feed_url)
        return element

    def _build_item(
        self, parent: ET.Element, podcast_name: str, episode: Episode, channel: PodcastChannelModel
    ) -> None:
        add = self._add
        model = episode.model
        path = episode.path
        description = model.description or ""
        explicit = channel.explicit if model.explicit is None else model.explicit
        duration = model.duration_hms or MediaProcessor.format_itunes_duration(
            MediaProcessor.get_duration_seconds(path)
        )
        try:
            length = path.stat().st_size
        except OSError:
            length = 0

        item = add(parent, "item")
        add(
            item,
            "guid",
            model.guid or hashlib.sha1(f"{podcast_name}/{path.name}".encode("utf-8")).hexdigest(),
            {"isPermaLink": "false"},
        )
        add(item, "title", model.title or path.stem)
        self._add_optional(item, "description", description)
        add(item, "pubDate", rfc2822_date(episode.published))
        add(
            item,
            "enclosure",
            attrib={
                "url": EpisodeManager.media_url(podcast_name, path.name),
                "length": str(length),
                "type": EpisodeManager.media_type(path),
            },
        )
        add(item, f"{IT}explicit", self._explicit(explicit))
        self._add_optional(item, f"{IT}author", model.author_name or channel.author_name)
        self._add_optional(item, f"{IT}duration", duration)
        self._add_optional(item, f"{IT}subtitle", model.subtitle)
        self._add_optional(item, f"{IT}summary", model.summary or description)

        image = EpisodeManager.resolve_image_url(podcast_name, model.image)
        if image:
            add(item, f"{IT}image", attrib={"href": image})

        if model.season is not None:
            add(item, f"{IT}season", str(model.season))
        if model.episode is not None:
            add(item, f"{IT}episode", str(model.episode))
        if model.episode_type in EPISODE_TYPES:
            add(item, f"{IT}episodeType", model.episode_type)

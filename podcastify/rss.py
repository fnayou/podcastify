import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from xml.sax.saxutils import escape

from podcastify.config import Config
from podcastify.logging_config import get_logger
from podcastify.media import MediaProcessor
from podcastify.parser import (
    EpisodeManager,
    _coerce_bool,
    rfc2822_date,
)

logger = get_logger(__name__)


class RSSGenerator:
    @staticmethod
    def xml_escape(value: Any) -> str:
        return escape(str(value), {'"': "&quot;"}) if value is not None else ""

    @staticmethod
    def build_itunes_categories(categories: Union[str, List[Any], Dict[str, Any]]) -> str:
        if not categories:
            return ""

        def esc_attr(value: str) -> str:
            return escape(value, {'"': "&quot;"})

        cats_xml: List[str] = []

        def add_category(parent: Optional[str], subcategory: Optional[str] = None) -> None:
            if not isinstance(parent, str) or not parent.strip():
                return
            if isinstance(subcategory, str) and subcategory.strip():
                cats_xml.append(
                    f'    <itunes:category text="{esc_attr(parent)}">\n'
                    f'      <itunes:category text="{esc_attr(subcategory)}"/>\n'
                    f'    </itunes:category>'
                )
            else:
                cats_xml.append(f'    <itunes:category text="{esc_attr(parent)}"/>')

        if isinstance(categories, str):
            add_category(categories)
        elif isinstance(categories, list):
            for item in categories:
                if isinstance(item, str):
                    add_category(item)
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    parent = item[0] if isinstance(item[0], str) else None
                    sub = item[1] if isinstance(item[1], str) else None
                    add_category(parent, sub)
                elif isinstance(item, dict):
                    parent = item.get("name")
                    sub = item.get("sub")
                    parent_s = parent if isinstance(parent, str) else None
                    sub_s = sub if isinstance(sub, str) else None
                    add_category(parent_s, sub_s)
        elif isinstance(categories, dict):
            parent = categories.get("name")
            sub = categories.get("sub")
            parent_s = parent if isinstance(parent, str) else None
            sub_s = sub if isinstance(sub, str) else None
            add_category(parent_s, sub_s)

        return "\n".join(cats_xml)

    def generate_feed_xml(
        self, podcast_name: str, metadata: Dict[str, Any], episodes: List[Dict[str, Any]]
    ) -> str:
        logger.debug(f"Render channel: {podcast_name}")
        now = rfc2822_date(datetime.now(timezone.utc))
        channel_xml = self._build_channel_metadata(podcast_name, metadata, now)
        items_xml = []
        for e in episodes:
            logger.debug(f"Build episode item: {e.get('file', 'unknown')}")
            items_xml.append(self._build_episode_item(podcast_name, e, metadata))
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
{channel_xml}
{chr(10).join(items_xml)}
  </channel>
</rss>"""

    def _build_channel_metadata(
        self, podcast_name: str, metadata: Dict[str, Any], timestamp: str
    ) -> str:
        esc = self.xml_escape
        title = metadata.get("title") or podcast_name
        link = metadata.get("link") or Config.BASE_URL
        description = metadata.get("description") or ""
        subtitle = metadata.get("subtitle")
        summary = metadata.get("summary") or description
        language = metadata.get("language") or "en"
        explicit = _coerce_bool(metadata.get("explicit"), False)
        author = metadata.get("author-name") or ""
        owner_name = metadata.get("author-name") or ""
        owner_email = metadata.get("author-email") or ""

        parts: List[str] = [
            f"    <title>{esc(title)}</title>",
            f"    <link>{esc(link)}</link>",
            f"    <description><![CDATA[{description}]]></description>"
            if description.strip()
            else "    <description></description>",
            f"    <language>{esc(language)}</language>",
            "    <generator>podcastify</generator>",
            f"    <lastBuildDate>{timestamp}</lastBuildDate>",
            f"    <itunes:explicit>{'yes' if explicit else 'no'}</itunes:explicit>",
            f"    <itunes:author>{esc(author)}</itunes:author>",
        ]

        if subtitle:
            parts.append(f"    <itunes:subtitle>{esc(subtitle)}</itunes:subtitle>")

        if summary and summary.strip():
            parts.append(f"    <itunes:summary><![CDATA[{summary}]]></itunes:summary>")
        else:
            parts.append("    <itunes:summary></itunes:summary>")

        img_url = EpisodeManager.resolve_image_url(podcast_name, metadata)
        if img_url:
            parts.append(f'    <itunes:image href="{esc(img_url)}"/>')

        if owner_name or owner_email:
            owner = ["    <itunes:owner>"]
            if owner_name:
                owner.append(f"      <itunes:name>{esc(owner_name)}</itunes:name>")
            if owner_email:
                owner.append(f"      <itunes:email>{esc(owner_email)}</itunes:email>")
            owner.append("    </itunes:owner>")
            parts.append("\n".join(owner))

        cats = self.build_itunes_categories(metadata.get("categories"))
        if cats:
            parts.append(cats)

        ptype = metadata.get("type")
        if ptype in ("episodic", "serial"):
            parts.append(f"    <itunes:type>{ptype}</itunes:type>")

        if metadata.get("block"):
            parts.append("    <itunes:block>yes</itunes:block>")

        if metadata.get("complete"):
            parts.append("    <itunes:complete>yes</itunes:complete>")

        new_feed_url = metadata.get("new_feed_url")
        if new_feed_url:
            parts.append(f"    <itunes:new-feed-url>{esc(new_feed_url)}</itunes:new-feed-url>")

        return "\n".join(parts)

    def _build_episode_item(
        self, podcast_name: str, episode: Dict[str, Any], channel_meta: Dict[str, Any]
    ) -> str:
        esc = self.xml_escape
        file_path = episode.get("__resolved_path")
        if not isinstance(file_path, Path):
            file_path = Path(str(file_path))

        fname = file_path.name
        media_url = f"{Config.BASE_URL}/{podcast_name}/{fname}"

        try:
            stat_result = file_path.stat()
        except (OSError, FileNotFoundError):
            stat_result = None

        length = stat_result.st_size if stat_result else 0

        pub_str = episode.get("pub_date")
        if pub_str:
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                logger.debug(f"Parse pub_date: {fname} -> {pub_dt}")
            except (ValueError, AttributeError):
                logger.warning(f"Invalid pub_date for {fname}: {pub_str}")
                pub_dt = datetime.fromtimestamp(
                    stat_result.st_mtime if stat_result else 0, tz=timezone.utc
                )
        else:
            pub_dt = datetime.fromtimestamp(
                stat_result.st_mtime if stat_result else 0, tz=timezone.utc
            )

        guid_val = episode.get("guid") or hashlib.sha1(
            f"{podcast_name}/{fname}".encode("utf-8")
        ).hexdigest()

        title = episode.get("title") or file_path.stem
        desc = episode.get("description") or ""
        summary = episode.get("summary") or desc
        subtitle = episode.get("subtitle")
        author = episode.get("author-name") or channel_meta.get("author-name", "")
        explicit = episode.get("explicit")
        explicit = (
            _coerce_bool(channel_meta.get("explicit"))
            if explicit is None
            else _coerce_bool(explicit)
        )

        dur_hms = episode.get("duration_hms")
        if not dur_hms:
            dur_sec = MediaProcessor.get_duration_seconds(file_path)
            dur_hms = MediaProcessor.format_itunes_duration(dur_sec)

        parts: List[str] = [
            "    <item>",
            f'      <guid isPermaLink="false">{esc(guid_val)}</guid>',
            f"      <title>{esc(title)}</title>",
            f"      <description><![CDATA[{desc}]]></description>"
            if desc.strip()
            else "      <description></description>",
            f"      <pubDate>{rfc2822_date(pub_dt)}</pubDate>",
            f'      <enclosure url="{esc(media_url)}" length="{length}" type="audio/mpeg"/>',
            f"      <itunes:explicit>{'yes' if explicit else 'no'}</itunes:explicit>",
            f"      <itunes:author>{esc(author)}</itunes:author>",
        ]

        if dur_hms:
            parts.append(f"      <itunes:duration>{dur_hms}</itunes:duration>")
        if subtitle:
            parts.append(f"      <itunes:subtitle>{esc(subtitle)}</itunes:subtitle>")
        if summary and summary.strip():
            parts.append(f"      <itunes:summary><![CDATA[{summary}]]></itunes:summary>")
        else:
            parts.append("      <itunes:summary></itunes:summary>")

        ep_img = EpisodeManager.resolve_image_url(podcast_name, episode)
        if ep_img:
            parts.append(f'      <itunes:image href="{esc(ep_img)}"/>')

        season = episode.get("season")
        if isinstance(season, int):
            parts.append(f"      <itunes:season>{season}</itunes:season>")
        ep_no = episode.get("episode")
        if isinstance(ep_no, int):
            parts.append(f"      <itunes:episode>{ep_no}</itunes:episode>")
        ep_type = episode.get("episode_type")
        if ep_type in ("full", "trailer", "bonus"):
            parts.append(f"      <itunes:episodeType>{ep_type}</itunes:episodeType>")

        parts.append("    </item>")
        return "\n".join(parts)

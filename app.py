#!/usr/bin/env python3
"""
Optimized Podcast RSS Generator
==============================

A Python script that automatically generates RSS feeds for podcast directories.
Scans for podcast configuration files and MP3 episodes, then creates iTunes-compatible RSS XML feeds.

Directory Structure:
  /app/podcasts/        # Configuration files (*-podcast.yaml)
  /app/public/          # Media files and generated RSS feeds
    /<podcast-name>/    # Individual podcast directories with MP3s (and images)
    <podcast-name>.xml  # Generated RSS feed
"""

import os
import sys
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Tuple, Any
import email.utils as eut
import yaml
from xml.sax.saxutils import escape


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class Config:
    """Centralized configuration management."""
    PODCASTS_ROOT = Path(os.environ.get("PODCASTS_ROOT", "/app/podcasts"))
    PUBLIC_ROOT = Path(os.environ.get("PUBLIC_ROOT", "/app/public"))
    BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8080")
    PUBLISH_XML = os.environ.get("PUBLISH_XML", "true").lower() == "true"
    RUN_ON_START = os.environ.get("RUN_ON_START", "true").lower() == "true"

    # Supported channel metadata fields
    CHANNEL_FIELDS = [
        "name", "title", "author-name", "author-email", "subtitle",
        "summary", "description", "language", "explicit", "image",
        "link", "categories", "type", "block", "complete", "new_feed_url"
    ]

    # Supported episode metadata fields (for reference)
    EPISODE_FIELDS = [
        "title", "description", "summary", "subtitle", "pub_date",
        "image", "explicit", "author-name", "season", "episode",
        "episode_type", "guid", "duration_hms"
    ]


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Simple logging with flush."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def rfc2822_date(dt: datetime) -> str:
    """Convert datetime to RFC 2822 format for RSS."""
    return eut.format_datetime(dt.astimezone(timezone.utc))


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------

class MediaProcessor:
    """Handles media file operations and metadata extraction."""

    @staticmethod
    def get_duration_seconds(mp3_path: Path) -> Optional[float]:
        """Extract duration from MP3 using ffprobe with error handling."""
        if not mp3_path.exists():
            return None
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1",
                    str(mp3_path)
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
            log(f"[WARN] Failed to get duration for {mp3_path.name}: {e}")
            return None

    @staticmethod
    def format_itunes_duration(seconds: Optional[float]) -> Optional[str]:
        """Format duration as iTunes-compatible HH:MM:SS or MM:SS string."""
        if seconds is None:
            return None
        total = max(0, int(round(seconds)))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------------------------------------------------------------------------
# Config management
# ---------------------------------------------------------------------------

class ConfigurationManager:
    """Handles YAML configuration loading and extraction."""

    @staticmethod
    def load_yaml(path: Path) -> Dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError) as e:
            log(f"[ERROR] Failed to load config {path}: {e}")
            return {}

    @staticmethod
    def extract_podcast_metadata(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract podcast metadata from config, supporting both flat and nested schemas.
        Back-compat: 'author' -> 'author-name'.
        """
        source = config.get("podcast", {}) if isinstance(config.get("podcast"), dict) else config
        meta = {k: source.get(k) for k in Config.CHANNEL_FIELDS if k in source}
        if not meta.get("author-name") and "author" in source:
            meta["author-name"] = source["author"]
        return meta

    @staticmethod
    def discover_podcast_configs() -> List[Tuple[str, Path]]:
        """Find all *-podcast.yaml files and derive podcast names."""
        if not Config.PODCASTS_ROOT.exists():
            log(f"[WARN] Podcasts directory not found: {Config.PODCASTS_ROOT}")
            return []
        configs: List[Tuple[str, Path]] = []
        for cfg in sorted(Config.PODCASTS_ROOT.iterdir()):
            if not cfg.is_file():
                continue
            name = cfg.name
            if name.endswith(("-podcast.yaml", "-podcast.yml")):
                pod_name = name.rsplit("-podcast.", 1)[0]
                configs.append((pod_name, cfg))
        return configs


# ---------------------------------------------------------------------------
# Episode management
# ---------------------------------------------------------------------------

class EpisodeManager:
    """Manages episode discovery and metadata processing."""

    @staticmethod
    def discover_episodes(podcast_name: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Discover episodes either from explicit config or by auto-scanning MP3 files.
        Returns list of episode dictionaries with resolved file paths.
        """
        pub_dir = Config.PUBLIC_ROOT / podcast_name
        eps = config.get("episodes")
        if eps:
            for e in eps:
                fname = Path(e.get("file", "")).name  # basename only (no subdirs)
                e["__resolved_path"] = pub_dir / fname
            return eps

        if not pub_dir.exists():
            return []

        discovered: List[Dict[str, Any]] = []
        for mp3 in sorted(pub_dir.glob("*.mp3")):
            discovered.append({
                "file": mp3.name,
                "title": mp3.stem,
                "__resolved_path": mp3
            })
        return discovered

    @staticmethod
    def resolve_image_url(podcast_name: str, meta: Dict[str, Any]) -> Optional[str]:
        """Resolve image URL from local file (in /public/<name>) or absolute URL."""
        img = meta.get("image")
        if not img:
            return None
        if isinstance(img, str) and img.startswith(("http://", "https://")):
            return img
        img_path = Config.PUBLIC_ROOT / podcast_name / Path(img).name
        if img_path.exists():
            return f"{Config.BASE_URL}/{podcast_name}/{img_path.name}"
        log(f"[WARN] Image file not found: {img_path}")
        return None


# ---------------------------------------------------------------------------
# RSS generation
# ---------------------------------------------------------------------------

class RSSGenerator:
    """Generates iTunes-compatible RSS XML feeds."""

    @staticmethod
    def xml_escape(value: Any) -> str:
        return escape(str(value), {'"': "&quot;"}) if value is not None else ""

    @staticmethod
    def build_itunes_categories(categories: Union[str, List[Any], Dict[str, Any]]) -> str:
        """
        Build iTunes category XML from flexible inputs, with strict typing for Pyright.
        Accepts:
          - "Technology"
          - ["Technology","Education"]
          - [["Society & Culture","Personal Journals"], ...]
          - [{"name":"Society & Culture","sub":"Personal Journals"}, ...]
        """
        if not categories:
            return ""

        def esc_attr(value: str) -> str:
            from xml.sax.saxutils import escape as _esc
            return _esc(value, {'"': "&quot;"})

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
                    sub    = item[1] if isinstance(item[1], str) else None
                    add_category(parent, sub)
                elif isinstance(item, dict):
                    parent = item.get("name")
                    sub    = item.get("sub")
                    parent_s = parent if isinstance(parent, str) else None
                    sub_s    = sub if isinstance(sub, str) else None
                    add_category(parent_s, sub_s)

        elif isinstance(categories, dict):
            parent = categories.get("name")
            sub    = categories.get("sub")
            parent_s = parent if isinstance(parent, str) else None
            sub_s    = sub if isinstance(sub, str) else None
            add_category(parent_s, sub_s)

        return "\n".join(cats_xml)

    def generate_feed_xml(self, podcast_name: str, metadata: Dict[str, Any], episodes: List[Dict[str, Any]]) -> str:
        """Generate complete RSS XML feed for podcast."""
        now = rfc2822_date(datetime.now(timezone.utc))
        channel_xml = self._build_channel_metadata(podcast_name, metadata, now)
        items_xml: List[str] = [self._build_episode_item(podcast_name, e, metadata) for e in episodes]
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
{channel_xml}
{chr(10).join(items_xml)}
  </channel>
</rss>"""

    def _build_channel_metadata(self, podcast_name: str, metadata: Dict[str, Any], timestamp: str) -> str:
        esc = self.xml_escape

        title = metadata.get("title") or podcast_name
        link = metadata.get("link") or Config.BASE_URL
        description = metadata.get("description") or ""
        subtitle = metadata.get("subtitle")
        summary = metadata.get("summary") or description
        language = metadata.get("language") or "en"
        explicit = bool(metadata.get("explicit", False))
        author = metadata.get("author-name") or ""
        owner_name = metadata.get("author-name") or ""
        owner_email = metadata.get("author-email") or ""

        parts: List[str] = [
            f"    <title>{esc(title)}</title>",
            f"    <link>{esc(link)}</link>",
            f"    <description><![CDATA[{description}]]></description>" if description.strip() else "    <description></description>",
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

    def _build_episode_item(self, podcast_name: str, episode: Dict[str, Any], channel_meta: Dict[str, Any]) -> str:
        esc = self.xml_escape
        file_path = episode.get("__resolved_path")
        if not isinstance(file_path, Path):
            file_path = Path(str(file_path))

        fname = file_path.name
        media_url = f"{Config.BASE_URL}/{podcast_name}/{fname}"
        length = file_path.stat().st_size if file_path.exists() else 0

        # pubDate
        pub_str = episode.get("pub_date")
        if pub_str:
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                log(f"[WARN] Invalid pub_date for {fname}: {pub_str}")
                pub_dt = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        else:
            pub_dt = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)

        # GUID
        guid_val = episode.get("guid") or hashlib.sha1(f"{podcast_name}/{fname}".encode("utf-8")).hexdigest()

        # Fields (inherit from channel)
        title = episode.get("title") or file_path.stem
        desc = episode.get("description") or ""
        summary = episode.get("summary") or desc
        subtitle = episode.get("subtitle")
        author = episode.get("author-name") or channel_meta.get("author-name", "")
        explicit = episode.get("explicit")
        explicit = bool(channel_meta.get("explicit", False)) if explicit is None else bool(explicit)

        dur_hms = episode.get("duration_hms")
        if not dur_hms:
            dur_sec = MediaProcessor.get_duration_seconds(file_path)
            dur_hms = MediaProcessor.format_itunes_duration(dur_sec)

        parts: List[str] = [
            "    <item>",
            f'      <guid isPermaLink="false">{esc(guid_val)}</guid>',
            f"      <title>{esc(title)}</title>",
            f"      <description><![CDATA[{desc}]]></description>" if desc.strip() else "      <description></description>",
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


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

class PodcastProcessor:
    """Main podcast processing orchestrator."""

    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.episode_manager = EpisodeManager()
        self.rss_generator = RSSGenerator()

    def process_podcast(self, podcast_name: str, config_path: Path) -> bool:
        try:
            cfg = self.config_manager.load_yaml(config_path)
            if not cfg:
                log(f"[ERROR] Empty or invalid config for {podcast_name}")
                return False

            meta = self.config_manager.extract_podcast_metadata(cfg)

            cfg_name = meta.get("name")
            if cfg_name and cfg_name != podcast_name:
                log(f"[WARN] Config name '{cfg_name}' differs from filename-derived name '{podcast_name}'; using '{podcast_name}'")

            pub_dir = Config.PUBLIC_ROOT / podcast_name
            if not pub_dir.exists():
                log(f"[WARN] Public directory missing for {podcast_name}: {pub_dir}")
                log("       Create directory and place MP3 files there")
                return False

            episodes = self.episode_manager.discover_episodes(podcast_name, cfg)
            if not episodes:
                log(f"[WARN] No episodes found for {podcast_name} in {pub_dir}")
                return False

            # Sort newest first (by pub_date if present, else file mtime)
            def _ep_ts(ep: Dict[str, Any]) -> float:
                pd = ep.get("pub_date")
                if pd:
                    try:
                        return datetime.fromisoformat(pd.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        pass
                p = ep.get("__resolved_path")
                try:
                    pth = p if isinstance(p, Path) else Path(str(p))
                    return pth.stat().st_mtime
                except Exception:
                    return 0.0

            episodes.sort(key=_ep_ts, reverse=True)

            # Warn for missing files
            missing = [e.get("file", "unknown") for e in episodes
                       if not Path(e.get("__resolved_path")).exists()]
            if missing:
                log(f"[WARN] Missing episode files for {podcast_name}: {', '.join(missing)}")

            if Config.PUBLISH_XML:
                xml = self.rss_generator.generate_feed_xml(podcast_name, meta, episodes)
                out = Config.PUBLIC_ROOT / f"{podcast_name}.xml"
                out.write_text(xml, encoding="utf-8")
                log(f"[OK] Published {podcast_name}: {len(episodes)} episodes -> {out}")
            else:
                log(f"[OK] Validated {podcast_name}: {len(episodes)} episodes (XML publishing disabled)")

            return True

        except Exception as e:
            log(f"[ERROR] Failed to process {podcast_name}: {e}")
            return False

    def process_all_podcasts(self) -> int:
        configs = self.config_manager.discover_podcast_configs()
        if not configs:
            log("[INFO] No podcast configurations found")
            log(f"       Place config files like '<name>-podcast.yaml' in {Config.PODCASTS_ROOT}")
            log(f"       Place media files in {Config.PUBLIC_ROOT}/<name>/")
            return 0

        log(f"[INFO] Found {len(configs)} podcast configuration(s)")
        ok = 0
        for name, cfg_path in configs:
            if self.process_podcast(name, cfg_path):
                ok += 1
        log(f"[INFO] Processing complete: {ok}/{len(configs)} successful")
        return ok


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> bool:
    log("Starting podcast RSS generator...")
    processor = PodcastProcessor()
    should_run = Config.RUN_ON_START or (len(sys.argv) > 1 and sys.argv[1] == "generate")
    if should_run:
        count = processor.process_all_podcasts()
        log(f"Generator finished: {count} podcast(s) processed")
        return count > 0
    else:
        log("Generator ready (set RUN_ON_START=true or use 'generate' argument to run)")
        return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

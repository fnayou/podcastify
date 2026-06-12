import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from podcastify.config import Config
from podcastify.logging_config import get_logger
from podcastify.media import MediaProcessor
from podcastify.parser import (
    ConfigurationManager,
    EpisodeManager,
    validate_podcast_config,
)
from podcastify.rss import RSSGenerator

logger = get_logger(__name__)


class PodcastProcessor:
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.episode_manager = EpisodeManager()
        self.rss_generator = RSSGenerator()

    def _build_metadata_from_model(self, model: Any) -> Dict[str, Any]:
        """Build metadata dict from validated PodcastChannelModel."""
        if not model:
            return {}
        meta = {}
        for field in Config.CHANNEL_FIELDS:
            field_alias = field
            if field == "author-name":
                value = getattr(model, "author_name", None)
            elif field == "author-email":
                value = getattr(model, "author_email", None)
            else:
                value = getattr(model, field, None)
            if value is not None:
                meta[field_alias] = value
        return meta

    def process_podcast(self, podcast_name: str, config_path: Path) -> bool:
        try:
            logger.debug(f"Processing podcast: {podcast_name}")
            cfg = self.config_manager.load_yaml(config_path)
            if not cfg:
                logger.error(f"Empty or invalid config for {podcast_name}")
                return False

            logger.debug(f"Config parsed: {config_path}")
            validated, err = validate_podcast_config(cfg)
            if err:
                logger.error(f"Config validation failed for {podcast_name}: {err}")
                return False

            meta = self._build_metadata_from_model(validated)
            if not meta:
                logger.error(f"Failed to build metadata for {podcast_name}")
                return False

            cfg_name = meta.get("name")
            if cfg_name and cfg_name != podcast_name:
                logger.warning(
                    f"Config name '{cfg_name}' differs from filename-derived "
                    f"name '{podcast_name}'; using '{podcast_name}'"
                )

            pub_dir = Config.PUBLIC_ROOT / podcast_name
            if not pub_dir.exists():
                logger.warning(f"Public directory missing for {podcast_name}: {pub_dir}")
                logger.info("Create directory and place MP3 files there")
                return False

            episodes = self.episode_manager.discover_episodes(
                podcast_name, cfg, validated
            )
            if not episodes:
                logger.warning(f"No episodes found for {podcast_name} in {pub_dir}")
                return False

            paths = [
                Path(e["__resolved_path"])
                for e in episodes
                if Path(e.get("__resolved_path", "")).exists()
            ]
            MediaProcessor.warm_durations_parallel(paths)

            def _ep_ts(ep: Dict[str, Any]) -> float:
                pd = ep.get("pub_date")
                if pd:
                    try:
                        return datetime.fromisoformat(
                            pd.replace("Z", "+00:00")
                        ).timestamp()
                    except Exception:
                        pass
                return ep.get("__mtime", 0.0)

            for ep in episodes:
                if "__mtime" not in ep:
                    p = ep.get("__resolved_path")
                    try:
                        pth = p if isinstance(p, Path) else Path(str(p))
                        ep["__mtime"] = pth.stat().st_mtime
                    except Exception:
                        ep["__mtime"] = 0.0

            episodes.sort(key=_ep_ts, reverse=True)

            logger.debug(f"Episode count: {podcast_name} -> {len(episodes)} episodes")
            logger.debug(f"Sort order: {podcast_name} by pub_date desc")

            missing = [
                e.get("file", "unknown")
                for e in episodes
                if not Path(e.get("__resolved_path")).exists()
            ]
            if missing:
                logger.warning(f"Missing episode files for {podcast_name}: {', '.join(missing)}")

            if Config.PUBLISH_XML:
                xml = self.rss_generator.generate_feed_xml(podcast_name, meta, episodes)
                out = Config.PUBLIC_ROOT / f"{podcast_name}.xml"
                logger.debug(f"Write path: {out}, bytes: {len(xml)}")
                fd, tmp = tempfile.mkstemp(dir=str(Config.PUBLIC_ROOT), suffix=".xml")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(xml)
                    # mkstemp creates 0600; feeds are public static files served
                    # by Caddy, so make them world-readable.
                    os.chmod(tmp, 0o644)
                    os.replace(tmp, str(out))
                except Exception:
                    os.unlink(tmp)
                    raise
                logger.info(f"Published {podcast_name}: {len(episodes)} episodes -> {out}")
            else:
                logger.info(
                    f"Validated {podcast_name}: {len(episodes)} episodes "
                    "(XML publishing disabled)"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to process {podcast_name}: {e}")
            return False

    def process_all_podcasts(self) -> int:
        configs = self.config_manager.discover_podcast_configs()
        if not configs:
            logger.info("No podcast configurations found")
            logger.info(f"Place config files like '<name>-podcast.yaml' in {Config.PODCASTS_ROOT}")
            logger.info(f"Place media files in {Config.PUBLIC_ROOT}/<name>/")
            return 0

        logger.info(f"Found {len(configs)} podcast configuration(s)")
        ok = 0
        for name, cfg_path in configs:
            if self.process_podcast(name, cfg_path):
                ok += 1
        logger.info(f"Processing complete: {ok}/{len(configs)} successful")
        return ok


def main() -> bool:
    logger.info("Starting podcast RSS generator")
    processor = PodcastProcessor()
    should_run = Config.RUN_ON_START or (len(sys.argv) > 1 and sys.argv[1] == "generate")
    if should_run:
        count = processor.process_all_podcasts()
        logger.info(f"Generator finished: {count} podcast(s) processed")
        return count > 0
    logger.info("Generator ready (set RUN_ON_START=true or use 'generate' argument to run)")
    return True

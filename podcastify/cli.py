import argparse
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from podcastify.config import Config
from podcastify.logging_config import configure_logging
from podcastify.media import MediaProcessor
from podcastify.parser import (
    ConfigurationManager,
    EpisodeManager,
    validate_podcast_config,
)
from podcastify.rss import RSSGenerator

logger = logging.getLogger(__name__)


class PodcastProcessor:
    TEMP_SUFFIX = ".xml.tmp"
    STALE_TEMP_AGE_SECONDS = 600

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
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
            if not Config.BASE_URL.startswith(("http://", "https://")):
                logger.error(
                    f"Invalid PUBLIC_BASE_URL '{Config.BASE_URL}' for {podcast_name}: "
                    "must start with http:// or https://"
                )
                return False
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

            discovered = self.episode_manager.discover_episodes(podcast_name, validated)
            episodes = []
            for e in discovered:
                if Path(e.get("__resolved_path", "")).exists():
                    episodes.append(e)
                else:
                    logger.warning(
                        f"Skipping episode for {podcast_name}: file not found: {e.get('file', 'unknown')}"
                    )
            skipped = len(discovered) - len(episodes)
            if not episodes:
                logger.warning(f"No episodes found for {podcast_name} in {pub_dir}")
                return False

            paths = [Path(e["__resolved_path"]) for e in episodes]
            MediaProcessor.warm_durations_parallel(paths)

            episodes.sort(key=lambda ep: ep["__published"], reverse=True)

            logger.debug(f"Episode count: {podcast_name} -> {len(episodes)} episodes")
            logger.debug(f"Sort order: {podcast_name} by pub_date desc")

            if Config.PUBLISH_XML and not self.dry_run:
                xml = self.rss_generator.generate_feed_xml(podcast_name, meta, episodes)
                out = Config.PUBLIC_ROOT / f"{podcast_name}.xml"
                logger.debug(f"Write path: {out}, bytes: {len(xml)}")
                fd, tmp = tempfile.mkstemp(
                    dir=str(Config.PUBLIC_ROOT),
                    prefix=f".{podcast_name}.",
                    suffix=self.TEMP_SUFFIX,
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(xml)
                        f.flush()
                        os.fsync(f.fileno())
                    # mkstemp creates 0600; feeds are public static files served
                    # by Caddy, so make them world-readable.
                    os.chmod(tmp, 0o644)
                    os.replace(tmp, str(out))
                except Exception:
                    os.unlink(tmp)
                    raise
                skipped_note = f" ({skipped} skipped)" if skipped else ""
                logger.info(f"Published {podcast_name}: {len(episodes)} episodes{skipped_note} -> {out}")
            else:
                logger.info(
                    f"Validated {podcast_name}: {len(episodes)} episodes "
                    "(XML publishing disabled)"
                )

            return True

        except Exception as e:
            logger.exception(f"Failed to process {podcast_name}: {e}")
            return False

    def remove_stale_temp_files(self) -> None:
        if self.dry_run or not Config.PUBLISH_XML or not Config.PUBLIC_ROOT.is_dir():
            return
        cutoff = time.time() - self.STALE_TEMP_AGE_SECONDS
        for tmp in Config.PUBLIC_ROOT.glob(f".*{self.TEMP_SUFFIX}"):
            try:
                if tmp.is_file() and tmp.stat().st_mtime < cutoff:
                    tmp.unlink()
                    logger.info(f"Removed stale temp file {tmp.name}")
            except OSError as e:
                logger.warning(f"Could not remove stale temp file {tmp.name}: {e}")

    def process_all_podcasts(self) -> int:
        self.remove_stale_temp_files()
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
        failed = len(configs) - ok
        logger.info(f"Processing complete: {ok}/{len(configs)} successful")
        return failed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.py", description="Podcastify RSS generator")
    subparsers = parser.add_subparsers(dest="command")
    generate = subparsers.add_parser("generate", help="generate feeds for every podcast config")
    generate.add_argument(
        "--dry-run",
        action="store_true",
        help="validate configs and episodes without writing feeds",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()
    logger.info("Starting podcast RSS generator")
    if args.command == "generate" or Config.RUN_ON_START:
        processor = PodcastProcessor(dry_run=getattr(args, "dry_run", False))
        failed = processor.process_all_podcasts()
        logger.info(f"Generator finished: {failed} podcast(s) failed")
        return 1 if failed else 0
    logger.info("Generator ready (set RUN_ON_START=true or use 'generate' argument to run)")
    return 0

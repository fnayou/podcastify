import argparse
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from podcastify.config import Config
from podcastify.logging_config import configure_logging
from podcastify.media import MediaProcessor
from podcastify.parser import (
    ConfigurationManager,
    Episode,
    EpisodeManager,
    validate_podcast_config,
)
from podcastify.rss import RSSGenerator

logger = logging.getLogger(__name__)


class PodcastProcessor:
    TEMP_SUFFIX = ".xml.tmp"
    STALE_TEMP_AGE_SECONDS = 600
    BUILD_DATE = re.compile(r"<lastBuildDate>[^<]*</lastBuildDate>")

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.config_manager = ConfigurationManager()
        self.episode_manager = EpisodeManager()
        self.rss_generator = RSSGenerator()

    @classmethod
    def _unchanged(cls, out: Path, xml: str) -> bool:
        try:
            current = out.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
        return cls.BUILD_DATE.sub("", current) == cls.BUILD_DATE.sub("", xml)

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
            if err or validated is None:
                logger.error(f"Config validation failed for {podcast_name}: {err or 'missing podcast configuration'}")
                return False

            cfg_name = validated.name
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
            episodes: List[Episode] = []
            for episode in discovered:
                if episode.path.exists():
                    episodes.append(episode)
                else:
                    logger.warning(f"Skipping episode for {podcast_name}: file not found: {episode.model.file}")
            skipped = len(discovered) - len(episodes)
            if not episodes:
                logger.warning(f"No episodes found for {podcast_name} in {pub_dir}")
                return False

            MediaProcessor.warm_durations([episode.path for episode in episodes])

            episodes.sort(key=lambda episode: episode.published, reverse=True)

            logger.debug(f"Episode count: {podcast_name} -> {len(episodes)} episodes")
            logger.debug(f"Sort order: {podcast_name} by pub_date desc")

            if Config.PUBLISH_XML and not self.dry_run:
                xml = self.rss_generator.generate_feed_xml(podcast_name, validated, episodes)
                out = Config.PUBLIC_ROOT / f"{podcast_name}.xml"
                if self._unchanged(out, xml):
                    logger.info(f"Unchanged {podcast_name}: {len(episodes)} episodes, kept {out}")
                    return True
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
                logger.info(f"Validated {podcast_name}: {len(episodes)} episodes (XML publishing disabled)")

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


class FeedWatcher:
    CONFIG_SUFFIXES = ("-podcast.yaml", "-podcast.yml")

    def __init__(self, processor: PodcastProcessor, interval: int, initial_run: bool = False):
        self.processor = processor
        self.interval = interval
        self.last: Optional[Tuple[Tuple[str, int, int], ...]] = None if initial_run else self.fingerprint()

    @classmethod
    def fingerprint(cls) -> Tuple[Tuple[str, int, int], ...]:
        candidates: List[Path] = []
        if Config.PODCASTS_ROOT.is_dir():
            candidates += [p for p in Config.PODCASTS_ROOT.iterdir() if p.name.endswith(cls.CONFIG_SUFFIXES)]
        if Config.PUBLIC_ROOT.is_dir():
            for pub_dir in Config.PUBLIC_ROOT.iterdir():
                if pub_dir.is_dir():
                    candidates += [p for p in pub_dir.iterdir() if p.suffix.lower() in Config.MEDIA_TYPES]
        entries = []
        for path in candidates:
            try:
                st = path.stat()
            except OSError:
                continue
            entries.append((str(path), st.st_size, st.st_mtime_ns))
        return tuple(sorted(entries))

    def check(self) -> Optional[int]:
        current = self.fingerprint()
        if current == self.last:
            return None
        self.last = current
        logger.info("Change detected; regenerating feeds")
        failed = self.processor.process_all_podcasts()
        if failed:
            logger.error(f"Regeneration finished: {failed} podcast(s) failed; retrying on the next change")
        else:
            logger.info("Regeneration finished: all podcasts processed")
        return failed

    def run(self) -> None:
        logger.info(f"Watching configs and media for changes every {self.interval}s")
        while True:
            time.sleep(self.interval)
            self.check()


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a whole number of seconds")
    if number < 1:
        raise argparse.ArgumentTypeError(f"interval must be at least 1 second, got {number}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.py", description="Podcastify RSS generator")
    subparsers = parser.add_subparsers(dest="command")
    generate = subparsers.add_parser("generate", help="generate feeds for every podcast config")
    generate.add_argument(
        "--dry-run",
        action="store_true",
        help="validate configs and episodes without writing feeds",
    )
    watch = subparsers.add_parser("watch", help="regenerate feeds when configs or media change")
    watch.add_argument(
        "--interval",
        type=_positive_int,
        required=True,
        help="seconds between change checks",
    )
    watch.add_argument(
        "--initial-run",
        action="store_true",
        help="regenerate on the first check even if nothing changed",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()
    logger.info("Starting podcast RSS generator")
    if args.command == "watch":
        FeedWatcher(PodcastProcessor(), interval=args.interval, initial_run=args.initial_run).run()
        return 0
    if args.command == "generate" or Config.RUN_ON_START:
        processor = PodcastProcessor(dry_run=getattr(args, "dry_run", False))
        failed = processor.process_all_podcasts()
        logger.info(f"Generator finished: {failed} podcast(s) failed")
        return 1 if failed else 0
    logger.info("Generator ready (set RUN_ON_START=true or use 'generate' argument to run)")
    return 0

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from podcastify.config import Config
from podcastify.media import MediaProcessor
from podcastify.parser import (
    ConfigurationManager,
    EpisodeManager,
    log,
    validate_podcast_config,
)
from podcastify.rss import RSSGenerator


class PodcastProcessor:
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

            validated, err = validate_podcast_config(cfg)
            if err:
                log(f"[ERROR] Config validation failed for {podcast_name}: {err}")
                return False

            meta = self.config_manager.extract_podcast_metadata(cfg)
            if validated:
                meta.setdefault("title", validated.title)
                meta.setdefault("description", validated.description)
                if validated.author_name:
                    meta.setdefault("author-name", validated.author_name)

            cfg_name = meta.get("name")
            if cfg_name and cfg_name != podcast_name:
                log(
                    f"[WARN] Config name '{cfg_name}' differs from filename-derived "
                    f"name '{podcast_name}'; using '{podcast_name}'"
                )

            pub_dir = Config.PUBLIC_ROOT / podcast_name
            if not pub_dir.exists():
                log(f"[WARN] Public directory missing for {podcast_name}: {pub_dir}")
                log("       Create directory and place MP3 files there")
                return False

            episodes = self.episode_manager.discover_episodes(
                podcast_name, cfg, validated
            )
            if not episodes:
                log(f"[WARN] No episodes found for {podcast_name} in {pub_dir}")
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

            missing = [
                e.get("file", "unknown")
                for e in episodes
                if not Path(e.get("__resolved_path")).exists()
            ]
            if missing:
                log(f"[WARN] Missing episode files for {podcast_name}: {', '.join(missing)}")

            if Config.PUBLISH_XML:
                xml = self.rss_generator.generate_feed_xml(podcast_name, meta, episodes)
                out = Config.PUBLIC_ROOT / f"{podcast_name}.xml"
                fd, tmp = tempfile.mkstemp(dir=str(Config.PUBLIC_ROOT), suffix=".xml")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(xml)
                    os.replace(tmp, str(out))
                except Exception:
                    os.unlink(tmp)
                    raise
                log(f"[OK] Published {podcast_name}: {len(episodes)} episodes -> {out}")
            else:
                log(
                    f"[OK] Validated {podcast_name}: {len(episodes)} episodes "
                    "(XML publishing disabled)"
                )

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


def main() -> bool:
    log("Starting podcast RSS generator...")
    processor = PodcastProcessor()
    should_run = Config.RUN_ON_START or (len(sys.argv) > 1 and sys.argv[1] == "generate")
    if should_run:
        count = processor.process_all_podcasts()
        log(f"Generator finished: {count} podcast(s) processed")
        return count > 0
    log("Generator ready (set RUN_ON_START=true or use 'generate' argument to run)")
    return True

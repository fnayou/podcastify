import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tinytag import TinyTag

from podcastify.config import Config

logger = logging.getLogger(__name__)

MIN_PLAUSIBLE_SECONDS = 1.0
IMPLAUSIBLE_MIN_BYTES = 100 * 1024


class MediaProcessor:
    CACHE_VERSION = 2

    _duration_cache: Dict[Tuple[str, float], Optional[float]] = {}
    _disk_loaded = False

    @classmethod
    def _cache_path(cls) -> Path:
        return Config.CACHE_ROOT / Config.CACHE_FILENAME

    @classmethod
    def _cache_key(cls, mp3_path: Path, mtime: float) -> str:
        return f"{mp3_path}|{mtime}"

    @classmethod
    def _load_disk_cache(cls) -> None:
        if cls._disk_loaded:
            return
        cls._disk_loaded = True

        cls._migrate_legacy_cache()

        path = cls._cache_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load duration cache: {e}")
            return
        if not isinstance(data, dict) or data.get("version") != cls.CACHE_VERSION:
            logger.info(f"Ignoring duration cache in an older format: {path}")
            return
        durations = data.get("durations")
        if not isinstance(durations, dict):
            return
        for key, val in durations.items():
            parts = key.rsplit("|", 1)
            if len(parts) == 2:
                try:
                    cls._duration_cache[(parts[0], float(parts[1]))] = val
                except ValueError:
                    continue

    @classmethod
    def _migrate_legacy_cache(cls) -> None:
        """Migrate cache from old PUBLIC_ROOT location to new CACHE_ROOT."""
        legacy_path = Config.PUBLIC_ROOT / Config.CACHE_FILENAME
        new_path = cls._cache_path()

        if legacy_path.exists() and not new_path.exists():
            try:
                legacy_data = json.loads(legacy_path.read_text(encoding="utf-8"))
                if isinstance(legacy_data, dict):
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    new_path.write_text(json.dumps(legacy_data), encoding="utf-8")
                    legacy_path.unlink()
                    logger.info(f"Migrated cache from {legacy_path} to {new_path}")
                    logger.debug(f"Cache migration: {len(legacy_data)} entries moved")
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to migrate legacy cache: {e}")

    @classmethod
    def _save_disk_cache(cls) -> None:
        path = cls._cache_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            newest: Dict[str, Tuple[float, Optional[float]]] = {}
            for (file_name, mtime), v in cls._duration_cache.items():
                if file_name not in newest or mtime > newest[file_name][0]:
                    newest[file_name] = (mtime, v)
            durations = {}
            for file_name, (mtime, v) in newest.items():
                file_path = Path(file_name)
                if file_path.exists():
                    durations[cls._cache_key(file_path, mtime)] = v
            # Atomic write: avoids a half-written cache if multiple saves race.
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps({"version": cls.CACHE_VERSION, "durations": durations}), encoding="utf-8")
            tmp.replace(path)
            logger.debug(f"Cache save: {len(durations)} entries written to {path}")
        except OSError as e:
            logger.warning(f"Failed to save duration cache: {e}")

    @classmethod
    def clear_cache(cls) -> None:
        cls._duration_cache.clear()
        cls._disk_loaded = False
        path = cls._cache_path()
        if path.exists():
            path.unlink(missing_ok=True)

    @classmethod
    def _store(cls, key: Tuple[str, float], duration: Optional[float], persist: bool) -> Optional[float]:
        cls._duration_cache[key] = duration
        if persist:
            cls._save_disk_cache()
        return duration

    @classmethod
    def _fail(cls, mp3_path: Path, key: Tuple[str, float], reason: str, persist: bool) -> None:
        logger.warning(f"Failed to get duration for {mp3_path.name}: {reason}")
        return cls._store(key, None, persist)

    @classmethod
    def get_duration_seconds(cls, mp3_path: Path, persist: bool = True) -> Optional[float]:
        if not mp3_path.exists():
            return None
        try:
            mtime = mp3_path.stat().st_mtime
        except (OSError, FileNotFoundError):
            return None
        key = (str(mp3_path), mtime)
        cls._load_disk_cache()
        if key in cls._duration_cache:
            cached = cls._duration_cache[key]
            logger.debug(f"Cache hit: {mp3_path.name} -> {cached}s")
            return cached

        try:
            file_size = mp3_path.stat().st_size
        except (OSError, FileNotFoundError):
            return cls._fail(mp3_path, key, "<size check failed>", persist)

        if file_size == 0:
            return cls._fail(mp3_path, key, "<zero-byte file>", persist)

        try:
            duration = TinyTag.get(str(mp3_path)).duration
        except Exception as e:
            return cls._fail(mp3_path, key, str(e) or type(e).__name__, persist)

        if duration is None:
            return cls._fail(mp3_path, key, "<no duration data>", persist)
        if not math.isfinite(duration) or duration <= 0:
            return cls._fail(mp3_path, key, f"<invalid duration {duration}>", persist)
        if duration < MIN_PLAUSIBLE_SECONDS and file_size >= IMPLAUSIBLE_MIN_BYTES:
            return cls._fail(mp3_path, key, f"<implausible duration {duration}s for {file_size} bytes>", persist)

        logger.debug(f"Resolved duration: {mp3_path.name} -> {duration}s")
        return cls._store(key, duration, persist)

    @classmethod
    def warm_durations(cls, paths: List[Path]) -> None:
        cls._load_disk_cache()
        for mp3_path in paths:
            if not mp3_path.exists():
                continue
            try:
                mtime = mp3_path.stat().st_mtime
            except OSError:
                continue
            if (str(mp3_path), mtime) not in cls._duration_cache:
                cls.get_duration_seconds(mp3_path, persist=False)
        cls._save_disk_cache()

    @staticmethod
    def format_itunes_duration(seconds: Optional[float]) -> Optional[str]:
        if seconds is None:
            return None
        total = max(0, int(round(seconds)))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

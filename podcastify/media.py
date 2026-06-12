import json
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from podcastify.config import Config
from podcastify.logging_config import get_logger

logger = get_logger(__name__)


class MediaProcessor:
    _duration_cache: Dict[Tuple[str, float], Optional[float]] = {}
    _disk_loaded = False
    # Guards _duration_cache against concurrent mutation/iteration when
    # warm_durations_parallel runs probes across a ThreadPoolExecutor.
    _lock = threading.Lock()

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
        with cls._lock:
            # Double-checked under the lock: parallel probes all call this.
            if cls._disk_loaded:
                return
            cls._disk_loaded = True

            cls._migrate_legacy_cache()

            path = cls._cache_path()
            if not path.exists():
                return
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for key, val in data.items():
                        parts = key.rsplit("|", 1)
                        if len(parts) == 2:
                            try:
                                cls._duration_cache[(parts[0], float(parts[1]))] = val
                            except ValueError:
                                continue
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load duration cache: {e}")

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
        # Snapshot under the lock so a concurrent probe inserting a key cannot
        # trigger "dictionary changed size during iteration".
        with cls._lock:
            items = list(cls._duration_cache.items())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {}
            for k, v in items:
                file_path = Path(k[0])
                if file_path.exists():
                    serializable[cls._cache_key(file_path, k[1])] = v
            # Atomic write: avoids a half-written cache if multiple saves race.
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(serializable), encoding="utf-8")
            tmp.replace(path)
            logger.debug(f"Cache save: {len(serializable)} entries written to {path}")
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
    def _cache_failure(cls, key: Tuple[str, float], persist: bool = True) -> None:
        with cls._lock:
            cls._duration_cache[key] = None
        if persist:
            cls._save_disk_cache()
        return None

    @classmethod
    def _run_ffprobe(cls, mp3_path: Path, extra_args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["ffprobe", "-v", "error", *extra_args, "-of", "default=nw=1:nk=1", str(mp3_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )

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

        # Short-circuit zero-byte files
        try:
            file_size = mp3_path.stat().st_size
        except (OSError, FileNotFoundError):
            logger.warning(f"Failed to get duration for {mp3_path.name}: <size check failed>")
            return cls._cache_failure(key, persist=persist)

        if file_size == 0:
            logger.warning(f"Failed to get duration for {mp3_path.name}: <zero-byte file>")
            return cls._cache_failure(key, persist=persist)

        try:
            logger.debug(f"ffprobe invocation: {mp3_path.name}")
            result = cls._run_ffprobe(mp3_path, ["-show_entries", "format=duration"])
            dur_str = result.stdout.strip()
            if not dur_str:
                dur, fallback_reason = cls._try_stream_duration_fallback(mp3_path)
                if dur is not None:
                    with cls._lock:
                        cls._duration_cache[key] = dur
                    if persist:
                        cls._save_disk_cache()
                    logger.debug(f"Resolved duration (stream fallback): {mp3_path.name} -> {dur}s")
                    return dur
                reason = fallback_reason or "<no duration data>"
                logger.warning(f"Failed to get duration for {mp3_path.name}: <no duration data> ({reason})")
                return cls._cache_failure(key, persist=persist)
            dur = float(dur_str)
            with cls._lock:
                cls._duration_cache[key] = dur
            if persist:
                cls._save_disk_cache()
            logger.debug(f"Resolved duration: {mp3_path.name} -> {dur}s")
            return dur
        except subprocess.CalledProcessError as e:
            stderr_msg = e.stderr.strip() if e.stderr else "<no stderr>"
            logger.warning(f"Failed to get duration for {mp3_path.name}: <exit {e.returncode}> ffprobe: {stderr_msg}")
            return cls._cache_failure(key, persist=persist)
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Failed to get duration for {mp3_path.name}: {e}")
            return cls._cache_failure(key, persist=persist)
        except ValueError as e:
            logger.warning(f"Failed to get duration for {mp3_path.name}: {e}")
            return cls._cache_failure(key, persist=persist)

    @classmethod
    def _try_stream_duration_fallback(cls, mp3_path: Path) -> Tuple[Optional[float], Optional[str]]:
        """Fallback: extract duration from audio stream when format=duration is empty.

        Returns:
            Tuple of (duration, reason). On success, reason is None.
            On failure, reason describes the error.
        """
        try:
            result = cls._run_ffprobe(
                mp3_path,
                ["-show_entries", "stream=duration", "-select_streams", "a:0"],
                timeout=10,
            )
            dur_str = result.stdout.strip()
            if not dur_str:
                return None, "<no stream duration data>"
            return float(dur_str), None
        except subprocess.CalledProcessError as e:
            stderr_msg = e.stderr.strip() if e.stderr else "<no stderr>"
            reason = f"<exit {e.returncode}> ffprobe: {stderr_msg}"
            return None, reason
        except subprocess.TimeoutExpired as e:
            return None, str(e)
        except ValueError as e:
            return None, str(e)

    @classmethod
    def warm_durations_parallel(cls, paths: List[Path], max_workers: int = 4) -> None:
        need_probe = []
        cls._load_disk_cache()
        for mp3_path in paths:
            if not mp3_path.exists():
                continue
            try:
                mtime = mp3_path.stat().st_mtime
            except OSError:
                continue
            key = (str(mp3_path), mtime)
            if key not in cls._duration_cache:
                need_probe.append(mp3_path)
        if not need_probe:
            return
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # persist=False: workers only mutate the in-memory cache (under the
            # lock). The disk cache is written once below, after all probes join,
            # instead of N times mid-flight (was O(N^2) writes + the race window).
            futures = {
                executor.submit(cls.get_duration_seconds, p, persist=False): p
                for p in need_probe
            }
            for future in as_completed(futures):
                future.result()
        cls._save_disk_cache()

    @staticmethod
    def format_itunes_duration(seconds: Optional[float]) -> Optional[str]:
        if seconds is None:
            return None
        total = max(0, int(round(seconds)))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from podcastify.config import Config
from podcastify.parser import log


class MediaProcessor:
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
            if isinstance(data, dict):
                for key, val in data.items():
                    parts = key.rsplit("|", 1)
                    if len(parts) == 2:
                        try:
                            cls._duration_cache[(parts[0], float(parts[1]))] = val
                        except ValueError:
                            continue
        except (OSError, json.JSONDecodeError) as e:
            log(f"[WARN] Failed to load duration cache: {e}")

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
                    log(f"[INFO] Migrated cache from {legacy_path} to {new_path}")
            except (OSError, json.JSONDecodeError) as e:
                log(f"[WARN] Failed to migrate legacy cache: {e}")

    @classmethod
    def _save_disk_cache(cls) -> None:
        path = cls._cache_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {}
            for k, v in cls._duration_cache.items():
                file_path = Path(k[0])
                if file_path.exists():
                    serializable[cls._cache_key(file_path, k[1])] = v
            path.write_text(json.dumps(serializable), encoding="utf-8")
        except OSError as e:
            log(f"[WARN] Failed to save duration cache: {e}")

    @classmethod
    def clear_cache(cls) -> None:
        cls._duration_cache.clear()
        cls._disk_loaded = False
        path = cls._cache_path()
        if path.exists():
            path.unlink(missing_ok=True)

    @classmethod
    def get_duration_seconds(cls, mp3_path: Path) -> Optional[float]:
        if not mp3_path.exists():
            return None
        try:
            mtime = mp3_path.stat().st_mtime
        except (OSError, FileNotFoundError):
            return None
        key = (str(mp3_path), mtime)
        cls._load_disk_cache()
        if key in cls._duration_cache:
            return cls._duration_cache[key]
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1",
                    str(mp3_path),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            dur = float(result.stdout.strip())
            cls._duration_cache[key] = dur
            cls._save_disk_cache()
            return dur
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
            log(f"[WARN] Failed to get duration for {mp3_path.name}: {e}")
            cls._duration_cache[key] = None
            cls._save_disk_cache()
            return None

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
            futures = {
                executor.submit(cls.get_duration_seconds, p): p
                for p in need_probe
            }
            for future in as_completed(futures):
                future.result()

    @staticmethod
    def format_itunes_duration(seconds: Optional[float]) -> Optional[str]:
        if seconds is None:
            return None
        total = max(0, int(round(seconds)))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

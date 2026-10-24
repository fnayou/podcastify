import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_TRUE_VALUES = ("true", "yes", "1", "on")
_FALSE_VALUES = ("false", "no", "0", "off", "")


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized not in _FALSE_VALUES:
            logger.warning(
                f"Unrecognised boolean value '{value}'; treating as false (use true/false, yes/no, 1/0 or on/off)"
            )
        return False
    return bool(value)


class _EnvVar:
    def __init__(self, key: str, default: Any, cast: Optional[Any] = None):
        self.key = key
        self.default = default
        self.cast = cast

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        val = os.environ.get(self.key, self.default)
        if self.cast:
            return self.cast(val)
        return val


class Config:
    PODCASTS_ROOT = _EnvVar("PODCASTS_ROOT", "/app/podcasts", lambda v: Path(v))
    PUBLIC_ROOT = _EnvVar("PUBLIC_ROOT", "/app/public", lambda v: Path(v))
    CACHE_ROOT = _EnvVar("CACHE_ROOT", "/app/.cache", lambda v: Path(v))
    BASE_URL = _EnvVar("PUBLIC_BASE_URL", "http://localhost:8080", lambda v: v.strip().rstrip("/"))
    PUBLISH_XML = _EnvVar("PUBLISH_XML", "true", _coerce_bool)
    PUBLISH_INDEX = _EnvVar("PUBLISH_INDEX", "false", _coerce_bool)
    RUN_ON_START = _EnvVar("RUN_ON_START", "true", _coerce_bool)
    LOG_LEVEL = _EnvVar("LOG_LEVEL", "INFO")

    MEDIA_TYPES = {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/x-m4a",
        ".mp4": "video/mp4",
        ".ogg": "audio/ogg",
        ".opus": "audio/opus",
    }

    DEFAULT_MEDIA_TYPE = "audio/mpeg"

    CACHE_FILENAME = ".podcastify-cache.json"

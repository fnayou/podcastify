import os
from pathlib import Path
from typing import Any, Optional


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
    BASE_URL = _EnvVar("PUBLIC_BASE_URL", "http://localhost:8080")
    PUBLISH_XML = _EnvVar("PUBLISH_XML", "true", lambda v: v.lower() == "true")
    RUN_ON_START = _EnvVar("RUN_ON_START", "true", lambda v: v.lower() == "true")

    CHANNEL_FIELDS = [
        "name", "title", "author-name", "author-email", "subtitle",
        "summary", "description", "language", "explicit", "image",
        "link", "categories", "type", "block", "complete", "new_feed_url",
    ]

    EPISODE_FIELDS = [
        "title", "description", "summary", "subtitle", "pub_date",
        "image", "explicit", "author-name", "season", "episode",
        "episode_type", "guid", "duration_hms",
    ]

    CACHE_FILENAME = ".podcastify-cache.json"

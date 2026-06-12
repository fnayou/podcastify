import email.utils as eut
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from podcastify.config import Config
from podcastify.logging_config import get_logger

logger = get_logger(__name__)


def rfc2822_date(dt: datetime) -> str:
    return eut.format_datetime(dt.astimezone(timezone.utc))


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1", "on")
    return bool(value)




def _sanitize_name(name: str) -> str:
    return name.replace("..", "").replace("/", "").replace("\\", "").strip()


class EpisodeModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    file: str
    title: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    subtitle: Optional[str] = None
    pub_date: Optional[str] = None
    image: Optional[str] = None
    explicit: Optional[bool] = None
    author_name: Optional[str] = Field(None, alias="author-name")
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_type: Optional[str] = None
    guid: Optional[str] = None
    duration_hms: Optional[str] = None


class PodcastChannelModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: Optional[str] = None
    title: str
    author_name: Optional[str] = Field(None, alias="author-name")
    author: Optional[str] = None
    author_email: Optional[str] = Field(None, alias="author-email")
    subtitle: Optional[str] = None
    summary: Optional[str] = None
    description: str
    language: Optional[str] = "en"
    explicit: Optional[bool] = False
    image: Optional[str] = None
    link: Optional[str] = None
    categories: Optional[Union[str, List[Any], Dict[str, Any]]] = None
    type: Optional[str] = None
    block: Optional[bool] = None
    complete: Optional[bool] = None
    new_feed_url: Optional[str] = None
    episodes: Optional[List[EpisodeModel]] = None

    @model_validator(mode="after")
    def map_legacy_author(self) -> "PodcastChannelModel":
        if not self.author_name and self.author:
            self.author_name = self.author
        return self

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("episodic", "serial"):
            raise ValueError("type must be 'episodic' or 'serial'")
        return v


class PodcastFileModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    podcast: Optional[PodcastChannelModel] = None

    @model_validator(mode="before")
    @classmethod
    def accept_flat_or_nested(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if isinstance(data.get("podcast"), dict):
            return data
        return {"podcast": data}


def validate_podcast_config(raw: Dict[str, Any]) -> Tuple[Optional[PodcastChannelModel], Optional[str]]:
    try:
        parsed = PodcastFileModel.model_validate(raw)
        channel = parsed.podcast
        if channel is None:
            return None, "missing podcast configuration"
        return channel, None
    except ValidationError as e:
        return None, str(e)


class ConfigurationManager:
    @staticmethod
    def load_yaml(path: Path) -> Dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError) as e:
            logger.error(f"Failed to load config {path}: {e}")
            return {}

    @staticmethod
    def extract_podcast_metadata(config: Dict[str, Any]) -> Dict[str, Any]:
        source = config.get("podcast", {}) if isinstance(config.get("podcast"), dict) else config
        meta = {k: source.get(k) for k in Config.CHANNEL_FIELDS if k in source}
        if not meta.get("author-name") and "author" in source:
            meta["author-name"] = source["author"]
        return meta

    @staticmethod
    def discover_podcast_configs() -> List[Tuple[str, Path]]:
        if not Config.PODCASTS_ROOT.exists():
            logger.warning(f"Podcasts directory not found: {Config.PODCASTS_ROOT}")
            logger.debug(f"Podcasts dir scan: {Config.PODCASTS_ROOT} does not exist")
            return []
        configs: List[Tuple[str, Path]] = []
        for cfg in sorted(Config.PODCASTS_ROOT.iterdir()):
            if not cfg.is_file():
                continue
            name = cfg.name
            if name.endswith(("-podcast.yaml", "-podcast.yml")):
                pod_name = _sanitize_name(name.rsplit("-podcast.", 1)[0])
                if not pod_name:
                    logger.warning(f"Skipping invalid podcast name from file: {cfg.name}")
                    continue
                logger.debug(f"Found podcast config: {cfg.name}")
                configs.append((pod_name, cfg))
        return configs


class EpisodeManager:
    @staticmethod
    def discover_episodes(
        podcast_name: str,
        config: Dict[str, Any],
        validated: Optional[PodcastChannelModel] = None,
    ) -> List[Dict[str, Any]]:
        pub_dir = Config.PUBLIC_ROOT / podcast_name
        eps = None
        if validated and validated.episodes is not None:
            eps = [ep.model_dump(by_alias=True) for ep in validated.episodes]
        else:
            eps = config.get("episodes")
        if eps:
            discovered: List[Dict[str, Any]] = []
            for e in eps:
                fname = Path(e.get("file", "")).name
                ep = dict(e)
                ep["__resolved_path"] = pub_dir / fname
                discovered.append(ep)
            return discovered

        if not pub_dir.exists():
            return []

        discovered = []
        for mp3 in sorted(pub_dir.glob("*.mp3")):
            discovered.append({
                "file": mp3.name,
                "title": mp3.stem,
                "__resolved_path": mp3,
            })
        return discovered

    @staticmethod
    def resolve_image_url(podcast_name: str, meta: Dict[str, Any]) -> Optional[str]:
        img = meta.get("image")
        if not img:
            return None
        if isinstance(img, str) and img.startswith(("http://", "https://")):
            return img
        img_path = Config.PUBLIC_ROOT / podcast_name / Path(img).name
        if img_path.exists():
            logger.debug(f"Resolved image: {img_path.name}")
            return f"{Config.BASE_URL}/{podcast_name}/{img_path.name}"
        logger.warning(f"Image file not found: {img_path}")
        return None
